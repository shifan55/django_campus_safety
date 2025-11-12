"""Reusable mixins shared across Django apps in the project."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import SystemLog


class AuditLogMixin:
    """Provide helper utilities for writing audit trail entries.

    The mixin is intentionally lightweight so it can be used both by
    class-based views (via inheritance) *and* by function-based views by
    directly calling :meth:`log_action`.  Storing the logic in one place keeps
    the logging format consistent everywhere in the project.
    """

    audit_log_object_type: Optional[str] = None

    @classmethod
    def log_action(
        cls,
        *,
        user,
        action_type: str,
        obj,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp=None,
    ) -> SystemLog:
        """Persist a :class:`~tccweb.core.models.SystemLog` record.

        Parameters
        ----------
        user:
            The authenticated user performing the action.
        action_type:
            One of :class:`SystemLog.ActionType` describing the event.
        obj:
            The model instance that the action was performed on.
        description:
            Optional human readable summary to help administrators.
        metadata:
            Optional JSON-serialisable payload for downstream analytics.
        timestamp:
            Override for when the action occurred. Defaults to ``timezone.now``.
        """

        if user is None or obj is None:
            raise ValueError("user and obj are required to log an action")

        object_type = cls.audit_log_object_type or obj.__class__.__name__
        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)

        log = SystemLog.objects.create(
            user=user,
            action_type=action_type,
            object_type=object_type,
            content_type=content_type,
            object_id=obj.pk,
            timestamp=timestamp or timezone.now(),
            description=description or "",
            metadata=metadata,
        )
        return log

    # Convenience wrappers that class-based views may call if desired.  These
    # helpers simply provide more descriptive names for common actions.
    @classmethod
    def log_view(cls, *, user, obj, description: Optional[str] = None, metadata=None):
        return cls.log_action(
            user=user,
            action_type=SystemLog.ActionType.VIEWED,
            obj=obj,
            description=description,
            metadata=metadata,
        )

    @classmethod
    def log_edit(cls, *, user, obj, description: Optional[str] = None, metadata=None):
        return cls.log_action(
            user=user,
            action_type=SystemLog.ActionType.EDITED,
            obj=obj,
            description=description,
            metadata=metadata,
        )

    @classmethod
    def log_close(cls, *, user, obj, description: Optional[str] = None, metadata=None):
        return cls.log_action(
            user=user,
            action_type=SystemLog.ActionType.CLOSED,
            obj=obj,
            description=description,
            metadata=metadata,
        )