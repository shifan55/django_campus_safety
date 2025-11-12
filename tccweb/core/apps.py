import logging

from django.apps import AppConfig
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tccweb.core'

    def ready(self):
        """Ensure Site and Google SocialApp records exist."""
        try:
            from django.contrib.sites.models import Site
            
            site, _ = Site.objects.get_or_create(
                id=settings.SITE_ID,
                defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_NAME},
            )
            site_needs_update = False
            if settings.SITE_DOMAIN and site.domain != settings.SITE_DOMAIN:
                site.domain = settings.SITE_DOMAIN
                site_needs_update = True
            if settings.SITE_NAME and site.name != settings.SITE_NAME:
                site.name = settings.SITE_NAME
                site_needs_update = True

            if site_needs_update:
                site.save(update_fields=["domain", "name"])
        except (OperationalError, ProgrammingError):
            # Database not ready
            return

        try:
            from allauth.socialaccount.models import SocialApp

            client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
            secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
            existing = (
                SocialApp.objects.filter(provider="google")
                .order_by("id")
                .prefetch_related("sites")
            )

            app = None
            if existing:
                app = existing[0]
                # Fold duplicate Google SocialApps into the primary record so
                # django-allauth never raises MultipleObjectsReturned.
                for duplicate in existing[1:]:
                    site_ids = list(duplicate.sites.values_list("id", flat=True))
                    if site_ids:
                        app.sites.add(*site_ids)
                    duplicate.delete()
            if client_id and secret:
                defaults = {
                    "name": "Google",
                    "client_id": client_id,
                    "secret": secret,
                }

                if app is None:
                    app = SocialApp.objects.create(provider="google", **defaults)
                else:
                    needs_save = False
                    for field, value in defaults.items():
                        if getattr(app, field) != value:
                            setattr(app, field, value)
                            needs_save = True

                    if needs_save:
                        app.save(update_fields=["name", "client_id", "secret"])
                
                if not app.sites.filter(id=settings.SITE_ID).exists():
                    app.sites.add(settings.SITE_ID)
        except (OperationalError, ProgrammingError, ImportError) as exc:
            logger.warning("Could not ensure SocialApp configuration: %s", exc)
    
        # Register signal handlers that capture authentication activity.
        try:
            from . import security_logging  # noqa: F401
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to initialise security logging: %s", exc)