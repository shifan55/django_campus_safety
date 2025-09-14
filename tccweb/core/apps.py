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
            Site.objects.get_or_create(
                id=settings.SITE_ID,
                defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_NAME},
            )
        except (OperationalError, ProgrammingError):
            # Database not ready
            return

        try:
            from allauth.socialaccount.models import SocialApp

            client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
            secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
            if client_id and secret:
                app, _ = SocialApp.objects.get_or_create(
                    provider="google",
                    defaults={
                        "name": "Google",
                        "client_id": client_id,
                        "secret": secret,
                    },
                )
                if not app.sites.filter(id=settings.SITE_ID).exists():
                    app.sites.add(settings.SITE_ID)
        except (OperationalError, ProgrammingError, ImportError) as exc:
            logger.warning("Could not ensure SocialApp configuration: %s", exc)