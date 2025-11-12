
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils import timezone
import os
import uuid
try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover - dependency may be missing in some envs
    Fernet = None

from .validators import (
    validate_file_size,
    validate_file_type,
    validate_no_malware,
)

def generate_tracking_code():
    """Generate a short unique tracking code for anonymous lookups."""
    return uuid.uuid4().hex[:10].upper()

def resource_file_path(instance, filename):
    """Generate a non-guessable filename for uploaded resources."""
    ext = os.path.splitext(filename)[1].lower()
    return f"resources/{uuid.uuid4().hex}{ext}"
resource_storage = FileSystemStorage(location=settings.PROTECTED_MEDIA_ROOT)


def validate_file_size(value):
    limit = 10 * 1024 * 1024  # 10 MB
    if value.size > limit:
        raise ValidationError("File size must not exceed 10 MB")


resource_storage = FileSystemStorage(location=settings.PROTECTED_MEDIA_ROOT)

class ReportType(models.TextChoices):
    BULLYING = 'bullying', 'Bullying'
    RAGGING = 'ragging', 'Ragging'
    HARASSMENT = 'harassment', 'Harassment'
    OTHER = 'other', 'Other'

class ReportStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    UNDER_REVIEW = 'under_review', 'Under Review'
    RESOLVED = 'resolved', 'Resolved'

class Report(models.Model):
    reporter = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports',
    )
    incident_type = models.CharField(max_length=32, choices=ReportType.choices)
    description = models.TextField()
    incident_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    witness_present = models.BooleanField(default=False)
    previous_incidents = models.BooleanField(default=False)
    support_needed = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    # optional meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reporter_name = models.CharField(max_length=100, blank=True, null=True)
    reporter_email = models.EmailField(blank=True, null=True)
    reporter_phone = models.CharField(max_length=20, blank=True, null=True)
    tracking_code = models.CharField(max_length=12, unique=True, default=generate_tracking_code, editable=False)

    status = models.CharField(
        max_length=50,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="assigned_reports",
        on_delete=models.SET_NULL,
    )
    
    assigned_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    counselor_notes = models.TextField(blank=True)
    
    awaiting_response = models.BooleanField(
        default=True,
        help_text="Whether the next action is expected from the assigned counselor.",
    )
    
    def __str__(self):
        return f"{self.get_incident_type_display()} on {self.incident_date:%Y-%m-%d}"
    def timeline_events(self):
        """Return ordered case timeline metadata for display."""

        events = [
            {
                "label": "Report created",
                "timestamp": self.created_at,
                "description": None,
                "icon": "calendar-day",
                "is_complete": True,
            }
        ]

        if self.assigned_to:
            events.append(
                {
                    "label": "Counselor assigned",
                    "timestamp": self.assigned_at or self.updated_at,
                    "description": (
                        self.assigned_to.get_full_name() or self.assigned_to.username
                    ),
                    "icon": "user-tie",
                    "is_complete": bool(self.assigned_at or self.updated_at),
                }
            )
        else:
            events.append(
                {
                    "label": "Counselor assigned",
                    "timestamp": None,
                    "description": "Awaiting assignment",
                    "icon": "user-tie",
                    "is_complete": False,
                }
            )

        if self.reporter_id:
            first_student_reply = (
                self.messages.filter(sender_id=self.reporter_id)
                .order_by("timestamp")
                .first()
            )
        else:
            first_student_reply = None

        events.append(
            {
                "label": "Student replied",
                "timestamp": first_student_reply.timestamp if first_student_reply else None,
                "description": None
                if first_student_reply
                else "Awaiting student response",
                "icon": "comment-dots",
                "is_complete": bool(first_student_reply),
            }
        )

        if self.status == ReportStatus.RESOLVED:
            events.append(
                {
                    "label": "Case closed",
                    "timestamp": self.resolved_at or self.updated_at,
                    "description": None,
                    "icon": "check-circle",
                    "is_complete": bool(self.resolved_at or self.updated_at),
                }
            )
        else:
            events.append(
                {
                    "label": "Case closed",
                    "timestamp": None,
                    "description": f"Status: {self.get_status_display()}",
                    "icon": "check-circle",
                    "is_complete": False,
                }
            )

        return events
    
    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reporter"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["assigned_at"]),
            models.Index(fields=["resolved_at"]),
        ]

class EducationalResource(models.Model):
    RESOURCE_TYPES = [
        ("article", "Article"),
        ("video", "Video"),
        ("guide", "Guide"),
        ("quiz", "Quiz"),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    url = models.URLField(blank=True)
    file = models.FileField(
        upload_to=resource_file_path,
        storage=resource_storage,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(["pdf", "mp4"]),
            validate_file_type,
            validate_file_size,
            validate_no_malware,
        ],
    )
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default="article")
    category = models.CharField(max_length=50, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_resources')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not getattr(self.file, "_encrypted", False):
            if Fernet is None:
                raise RuntimeError("cryptography library is required for file encryption")
            fernet = Fernet(settings.FILE_ENCRYPTION_KEY.encode())
            data = self.file.read()
            self.file = ContentFile(fernet.encrypt(data), name=self.file.name)
            self.file._encrypted = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["created_by"]),
        ]

class Quiz(models.Model):
    """A quiz consisting of multiple questions."""

    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["created_by"]),
        ]

class QuizQuestion(models.Model):
    """Individual question belonging to a Quiz."""

    OPTION_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]

    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200, blank=True)
    option_d = models.CharField(max_length=200, blank=True)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)

    def __str__(self):
        return self.text

    class Meta:
        indexes = [models.Index(fields=["quiz"])]

class SupportContact(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    office_hours = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [models.Index(fields=["created_at"])]


class SystemLog(models.Model):
    """Immutable audit trail used for tracking counselor actions."""

    class ActionType(models.TextChoices):
        """Supported actions that are tracked in the audit trail."""

        VIEWED = "VIEWED", "Viewed"
        EDITED = "EDITED", "Edited"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="system_logs",
        help_text="Actor who performed the action.",
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the action was performed.",
    )
    action_type = models.CharField(
        max_length=32,
        choices=ActionType.choices,
        help_text="High level category describing the action.",
    )
    object_type = models.CharField(
        max_length=128,
        help_text="Human readable label for the object type (e.g. Report).",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Generic reference to the model for the affected object.",
    )
    object_id = models.PositiveIntegerField(
        help_text="Primary key for the affected object.",
    )
    content_object = GenericForeignKey("content_type", "object_id")
    description = models.TextField(
        blank=True,
        help_text="Optional human readable description of what happened.",
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Structured metadata for integrations or analytics.",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["user", "timestamp"],
                name="systemlog_user_timestamp_idx",
            ),
        ]
        verbose_name = "System log entry"
        verbose_name_plural = "System log entries"

    def __str__(self) -> str:
        return f"{self.get_action_type_display()} {self.object_type} #{self.object_id}"
    
class SecurityLog(models.Model):
    """Capture authentication and permission related security events."""

    class EventType(models.TextChoices):
        """Enumerate the security-sensitive activities we monitor."""

        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login success"
        LOGIN_FAILURE = "LOGIN_FAILURE", "Login failure"
        LOGOUT = "LOGOUT", "Logout"
        PERMISSION_GRANTED = "PERMISSION_GRANTED", "Permission granted"
        PERMISSION_REVOKED = "PERMISSION_REVOKED", "Permission revoked"

    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the security event occurred.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="security_events",
        blank=True,
        null=True,
        help_text="Authenticated user who triggered the event (if known).",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="security_events_target",
        blank=True,
        null=True,
        help_text="Account affected by the change (can differ from actor).",
    )
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        help_text="Type of security event (login, permission change, etc.).",
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Best-effort IP address captured with the event.",
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Recorded User-Agent string for additional context.",
    )
    description = models.TextField(
        blank=True,
        help_text="Human readable explanation of what occurred.",
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Optional structured payload for downstream analysis.",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"], name="securitylog_ts_idx"),
            models.Index(
                fields=["event_type", "timestamp"],
                name="securitylog_event_ts_idx",
            ),
        ]
        verbose_name = "Security log entry"
        verbose_name_plural = "Security log entries"

    def __str__(self) -> str:
        actor = self.actor.get_username() if self.actor else "system"
        target = self.target_user.get_username() if self.target_user else "unknown"
        return f"{self.get_event_type_display()} {target} by {actor}"