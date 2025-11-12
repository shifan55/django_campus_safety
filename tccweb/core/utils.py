"""Utility helpers shared across the core application."""

from __future__ import annotations

import base64
import re
from io import BytesIO

from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

from django.apps import apps
from django.conf import settings
from django.urls import NoReverseMatch, reverse


@lru_cache(maxsize=1)
def get_totp_model():
    """Return the ``TOTPDevice`` model when the django-otp app is installed."""

    if not apps.is_installed("django_otp.plugins.otp_totp"):
        return None

    try:  # pragma: no cover - optional dependency
        from django_otp.plugins.otp_totp.models import TOTPDevice  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        return None

    return TOTPDevice


def get_user_totp_devices(user: Any, *, confirmed: Optional[bool] = None) -> List[Any]:
    """Return the user's TOTP devices filtered by confirmation state."""

    TOTPDevice = get_totp_model()
    if TOTPDevice is None or not user or not getattr(user, "is_authenticated", False):
        return []

    queryset = TOTPDevice.objects.filter(user=user)
    if confirmed is True:
        queryset = queryset.filter(confirmed=True)
    elif confirmed is False:
        queryset = queryset.filter(confirmed=False)

    return list(queryset.order_by("id"))


def verify_user_otp_token(user: Any, token: str) -> Optional[Any]:
    """Validate ``token`` against the user's confirmed TOTP devices."""

    # Accept codes that include spaces (for example "123 456") by removing all
    # whitespace before running the verification checks.
    token = re.sub(r"\s+", "", token or "")
    if not token or not token.isdigit():
        return None

    for device in get_user_totp_devices(user, confirmed=True):
        try:
            if device.verify_token(token):
                return device
        except Exception:  # pragma: no cover - defensive guard
            continue

    return None


def user_has_confirmed_2fa(user: Any) -> bool:
    """Return ``True`` when the given user has at least one confirmed 2FA device.

    The helper leans on django-two-factor-auth / django-otp primitives and is
    intentionally defensive: it prefers methods exposed by the authenticated
    user instance (``is_verified``), then falls back to database lookups for
    TOTP devices or the more generic ``django_otp.user_has_device`` helper.

    Keeping this logic here makes it straightforward to tweak banner behaviour
    globally (for example, to include backup tokens or WebAuthn devices).
    """

    if not user or not getattr(user, "is_authenticated", False):
        return False

    # django-two-factor-auth wires ``is_verified`` onto the user object when the
    # session has completed an OTP flow.  When present we can rely on it to
    # detect a verified session and shortcut the rest of the checks.
    is_verified_attr = getattr(user, "is_verified", None)
    if callable(is_verified_attr):
        try:
            if is_verified_attr():
                return True
        except TypeError:
            # Some integrations expose ``is_verified`` as a property.  Fallback
            # to evaluating it as a boolean below.
            pass
    if isinstance(is_verified_attr, bool) and is_verified_attr:
        return True

    # Otherwise we attempt to look up confirmed OTP devices explicitly.  The
    # import is kept inside the function to avoid ImportError at import time in
    # environments without django-two-factor-auth installed.
    PhoneDevice = None  # type: ignore[assignment]
    if apps.is_installed("two_factor"):
        try:  # pragma: no cover - optional dependency
            from two_factor.models import PhoneDevice as _PhoneDevice  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            pass
        else:
            PhoneDevice = _PhoneDevice

    totp_model = get_totp_model()
    if totp_model and get_user_totp_devices(user, confirmed=True):
        return True

    if PhoneDevice is not None:
        if PhoneDevice.objects.filter(user=user, confirmed=True).exists():
            return True

    try:  # pragma: no cover - optional dependency
        from django_otp import user_has_device  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        user_has_device = None  # type: ignore

    if user_has_device is not None:
        return bool(user_has_device(user, confirmed=True))

    # Finally honour the project-level flag which allows deployments without
    # the optional django-otp dependencies to track completion of the setup
    # flow. When dedicated OTP apps are available we rely on their state and do
    # not consider the legacy flag.
    if totp_model is None:
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "two_factor_enabled", False):
            return True

    # If the integration is not available we assume 2FA is not configured so
    # that we fail safe and allow the reminder banner to remain visible.
    return False


def resolve_2fa_setup_url(
    *,
    url_names: Optional[Iterable[str]] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    """Return the absolute URL for the 2FA setup view when available.

    ``django-two-factor-auth`` registers its setup view under the
    ``"two_factor:setup"`` URL name by default, but projects sometimes rename
    or wrap the view.  To keep the banner resilient we accept a list of
    candidate names (for example supplied via ``settings.TWO_FACTOR_SETUP_URL_NAME``)
    and fall back to an explicit URL value if provided.

    When no candidate resolves we return ``None`` so callers can choose whether
    to hide the banner or show an alternate call-to-action.
    """

    candidates: list[str] = []

    configured_name = getattr(settings, "TWO_FACTOR_SETUP_URL_NAME", None)
    if configured_name:
        if isinstance(configured_name, (list, tuple, set, frozenset)):
            candidates.extend(str(name) for name in configured_name)
        else:
            candidates.append(str(configured_name))

    if url_names:
        candidates.extend(str(name) for name in url_names)

    # Always try project-specific defaults before the django-two-factor-auth
    # namespace so customised names can take precedence.
    candidates.extend(
        [
            "enable-two-factor",
            "core:enable-two-factor",
            "two_factor:setup",
            "two_factor:profile",
        ]
    )

    for name in candidates:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue

    fallback_url = getattr(settings, "TWO_FACTOR_SETUP_URL", None)
    if fallback_url:
        return str(fallback_url)

    return default


def build_two_factor_context(user: Any) -> Dict[str, Any]:
    """Return common template context values for 2FA interfaces.

    Views that surface account settings (for example each portal's profile
    screen) can reuse this helper to expose a consistent set of variables to
    their templates without duplicating the underlying detection logic.
    """

    manage_url = resolve_2fa_setup_url()
    confirmed_devices = get_user_totp_devices(user, confirmed=True)
    return {
        "two_factor_enabled": user_has_confirmed_2fa(user),
        "two_factor_manage_url": manage_url,
        "two_factor_setup_url": manage_url,
        "two_factor_can_manage": bool(manage_url),
        "two_factor_devices": confirmed_devices,
        "two_factor_device_count": len(confirmed_devices),
    }


def generate_totp_qr_data_uri(otpauth_url: str) -> str:
    """Return a PNG data-URI QR code for ``otpauth_url`` when possible.

    The helper prefers to keep failures silent so the calling view can fall
    back to the manual authenticator key if QR generation libraries are not
    installed on the host environment.
    """

    otpauth_url = (otpauth_url or "").strip()
    if not otpauth_url:
        return ""

    try:  # pragma: no cover - optional dependency
        import qrcode
    except ImportError:  # pragma: no cover - optional dependency
        return ""

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(otpauth_url)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


__all__ = [
    "build_two_factor_context",
    "generate_totp_qr_data_uri",
    "get_totp_model",
    "get_user_totp_devices",
    "resolve_2fa_setup_url",
    "user_has_confirmed_2fa",
    "verify_user_otp_token",
]