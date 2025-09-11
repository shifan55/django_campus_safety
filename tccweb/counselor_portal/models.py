from django.db import models
from django.conf import settings
from tccweb.core.models import Report


class CaseNote(models.Model):
    """Private notes added by counselors for a report."""

    report = models.ForeignKey(Report, related_name="notes", on_delete=models.CASCADE)
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="case_notes",
        on_delete=models.CASCADE,
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Note on {self.report_id} by {self.counselor_id}"


class ChatMessage(models.Model):
    """Secure messages exchanged between students and counselors."""

    report = models.ForeignKey(Report, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="sent_messages",
        on_delete=models.CASCADE,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="received_messages",
        on_delete=models.CASCADE,
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"Msg from {self.sender_id} to {self.recipient_id}"