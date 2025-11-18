"""Django system checks for the core app.

These checks surface common misconfigurations that lead to Google OAuth
errors such as ``invalid_client``.
"""

from __future__ import annotations

from django.conf import settings
from django.core import checks


@checks.register()
def google_oauth_configured(app_configs, **kwargs):  # pragma: no cover - configuration check
    """Warn when Google OAuth is not fully configured.

    Returning warnings instead of errors keeps the site usable (fallback to
    username/password) while making the misconfiguration visible in ``check``
    output and the Django admin system check panel.
    """

    messages: list[checks.CheckMessage] = []

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        messages.append(
            checks.Warning(
                "Google OAuth client credentials are missing.",
                hint=(
                    "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars, then create"
                    " a Google OAuth client with the authorized redirect URI"
                    " https://%s/accounts/google/login/callback/." % settings.SITE_DOMAIN
                ),
                id="tccweb.W001",
            )
        )
        return messages

    try:
        from allauth.socialaccount.models import SocialApp

        social_app = (
            SocialApp.objects.filter(provider="google", client_id=client_id)
            .order_by("id")
            .first()
        )
    except Exception:
        # Avoid breaking startup if migrations haven't run yet; the warning
        # above should still guide configuration once the DB is ready.
        return messages

    if social_app is None:
        messages.append(
            checks.Warning(
                "No Google SocialApp matches the configured client ID.",
                hint=(
                    "Run migrations then set GOOGLE_CLIENT_ID/SECRET and restart so"
                    " the auto-provisioner can create the SocialApp, or create it"
                    " manually in the admin with the same client ID and site %s." % settings.SITE_ID
                ),
                id="tccweb.W002",
            )
        )

    return messages