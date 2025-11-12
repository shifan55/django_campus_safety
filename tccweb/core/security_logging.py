"""Signal handlers that persist security-sensitive audit events."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.contrib.auth.models import Permission
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import SecurityLog

logger = logging.getLogger(__name__)

UserModel = get_user_model()


def _get_client_ip(request) -> Optional[str]:
    """Extract the client IP address from the request object."""

    if request is None:
        return None

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # The left-most address is the original client in standard proxy setups.
        return x_forwarded_for.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def _get_user_agent(request) -> str:
    """Return the User-Agent header if one was supplied."""

    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


def _permission_codenames(pk_set: Iterable[int]) -> Iterable[str]:
    """Resolve permission primary keys into their human-friendly codenames."""

    if not pk_set:
        return []
    return Permission.objects.filter(pk__in=pk_set).values_list("codename", flat=True)


@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):  # pragma: no cover - requires Django runtime
    """Persist a record whenever a user signs in successfully."""

    session_key = None
    if getattr(request, "session", None) is not None:
        session_key = request.session.session_key

    SecurityLog.objects.create(
        actor=user,
        target_user=user,
        event_type=SecurityLog.EventType.LOGIN_SUCCESS,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        description=f"{user.get_username()} signed in successfully.",
        metadata={
            "path": getattr(request, "path", ""),
            "session_key": session_key,
        },
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):  # pragma: no cover - requires Django runtime
    """Record when a user signs out of the system."""

    SecurityLog.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        target_user=user if getattr(user, "is_authenticated", False) else None,
        event_type=SecurityLog.EventType.LOGOUT,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        description=(
            f"{getattr(user, 'get_username', lambda: 'Unknown')()} signed out."
            if getattr(user, "is_authenticated", False)
            else "Anonymous session ended."
        ),
        metadata={"path": getattr(request, "path", "")},
    )


@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):  # pragma: no cover
    """Capture failed authentication attempts for administrators to review."""

    username = (credentials or {}).get("username", "unknown")
    SecurityLog.objects.create(
        event_type=SecurityLog.EventType.LOGIN_FAILURE,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        description=f"Failed login attempt for username '{username}'.",
        metadata={
            "username": username,
            "path": getattr(request, "path", "") if request is not None else "",
        },
    )


@receiver(m2m_changed, sender=UserModel.user_permissions.through)
def log_permission_assignment(
    sender,
    instance,
    action,
    reverse,
    model,
    pk_set,
    **kwargs,
):  # pragma: no cover - depends on Django signal execution
    """Track when permissions are granted or revoked for a user."""

    if reverse or action not in {"post_add", "post_remove"}:
        return

    codename_list = list(_permission_codenames(pk_set))
    if not codename_list:
        return

    event_type = (
        SecurityLog.EventType.PERMISSION_GRANTED
        if action == "post_add"
        else SecurityLog.EventType.PERMISSION_REVOKED
    )

    change_label = "granted" if action == "post_add" else "revoked"
    SecurityLog.objects.create(
        actor=None,
        target_user=instance,
        event_type=event_type,
        description=(
            f"Permissions {', '.join(codename_list)} were {change_label} for "
            f"{instance.get_username() if hasattr(instance, 'get_username') else instance}."
        ),
        metadata={
            "permissions": codename_list,
            "action": change_label,
            "user_id": getattr(instance, "pk", None),
        },
    )