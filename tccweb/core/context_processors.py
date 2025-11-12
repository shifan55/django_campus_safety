# core/context_processors.py
from django.conf import settings

from .utils import resolve_2fa_setup_url, user_has_confirmed_2fa


def google_keys(request):
    return {
        "GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        "GOOGLE_CLIENT_ID": getattr(settings, "GOOGLE_CLIENT_ID", ""),
    }


def enable_2fa_banner(request):
    """Add a flag indicating if the 2FA reminder banner should be shown.

    The flag is ``True`` only when the request has an authenticated user who has
    not yet finished configuring two-factor authentication.  For anonymous
    visitors or users with confirmed 2FA devices, the banner remains hidden.
    """

    user = getattr(request, "user", None)
    should_show_banner = False
    setup_url = resolve_2fa_setup_url()

    if user and user.is_authenticated:
        # Reuse the central helper so we have a single place to adjust 2FA rules
        # (e.g., when adding support for backup tokens or other device types).
        should_show_banner = not user_has_confirmed_2fa(user)

    # If we cannot resolve a setup URL we avoid showing the banner, as the call
    # to action would otherwise be a dead end for the user.  Projects can define
    # ``TWO_FACTOR_SETUP_URL`` or ``TWO_FACTOR_SETUP_URL_NAME`` to provide the
    # appropriate destination.
    if should_show_banner and not setup_url:
        should_show_banner = False

    return {
        "enable_2fa_banner": should_show_banner,
        "enable_2fa_setup_url": setup_url,
    }