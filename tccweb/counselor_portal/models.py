from django.db import models
from django.conf import settings
from django.utils import timezone
from tccweb.core.models import Report
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import base64

"""Models supporting counselor case notes and secure messaging."""
class CounselorSpecialization(models.TextChoices):
    """Areas of expertise used by the smart assignment engine."""

    GENERAL = "general", "General Support"
    ACADEMIC = "academic", "Academic Guidance"
    EMOTIONAL = "emotional", "Emotional Wellness"
    DISCIPLINARY = "disciplinary", "Disciplinary & Safety"


class CounselorProfile(models.Model):
    """Metadata that powers smart counselor assignment."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="counselor_profile",
        on_delete=models.CASCADE,
    )
    specialization = models.CharField(
        max_length=32,
        choices=CounselorSpecialization.choices,
        default=CounselorSpecialization.GENERAL,
    )
    max_active_cases = models.PositiveIntegerField(default=25)
    auto_assign_enabled = models.BooleanField(default=True)
    last_auto_assigned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["specialization"], name="cns_profile_spec_idx"),
            models.Index(fields=["auto_assign_enabled"], name="cns_profile_auto_idx"),
        ]

    def mark_assigned_now(self):
        self.last_auto_assigned_at = timezone.now()
        self.save(update_fields=["last_auto_assigned_at"])

    def __str__(self):
        return f"CounselorProfile<{self.user_id}>"
    
class EmotionLabel(models.TextChoices):
    """Normalized set of detected emotional states for chat messages."""

    ANXIOUS = "anxious", "Anxious"
    ANGRY = "angry", "Angry"
    STRESSED = "stressed", "Stressed"
    CALM = "calm", "Calm"
    NEUTRAL = "neutral", "Neutral"


class RiskLevel(models.TextChoices):
    """Risk posture detected in the student's latest update."""

    NORMAL = "normal", "Stable"
    ELEVATED = "elevated", "Elevated"
    CRITICAL = "critical", "Critical"
    

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

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["report"]),
            models.Index(fields=["counselor"]),
        ]

class UserKey(models.Model):
    """RSA key pair for a user to support end-to-end message encryption."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="encryption_key",
        on_delete=models.CASCADE,
    )
    public_key = models.TextField()
    private_key = models.TextField()

    @classmethod
    def get_or_create(cls, user):
        try:
            return user.encryption_key
        except cls.DoesNotExist:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pub_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            priv_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            return cls.objects.create(
                user=user,
                public_key=pub_pem.decode(),
                private_key=priv_pem.decode(),
            )


class ChatMessage(models.Model):
    """End-to-end encrypted threaded messages for reports."""

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
    cipher_for_sender = models.TextField(blank=True, null=True)
    cipher_for_recipient = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="replies",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, db_index=True)
    attachment = models.FileField(
        upload_to="chat_attachments/",
        blank=True,
        null=True,
        help_text="Optional file shared within the conversation.",
    )
    
    emotion = models.CharField(
        max_length=16,
        choices=EmotionLabel.choices,
        default=EmotionLabel.NEUTRAL,
    )
    emotion_score = models.FloatField(default=0.0)
    emotion_confidence = models.FloatField(default=0.0)
    risk_level = models.CharField(
        max_length=16,
        choices=RiskLevel.choices,
        default=RiskLevel.NORMAL,
    )
    emotion_explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["report"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["recipient"]),
            models.Index(fields=["risk_level"], name="chat_msg_risk_idx"),
        ]

    @staticmethod
    def _encrypt_for(user, message: str) -> str:
        key = UserKey.get_or_create(user)
        public_key = serialization.load_pem_public_key(key.public_key.encode())
        cipher = public_key.encrypt(
            message.encode(),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        return base64.b64encode(cipher).decode()

    @staticmethod
    def _decrypt_for(user, cipher_text: str) -> str:
        key = UserKey.get_or_create(user)
        private_key = serialization.load_pem_private_key(key.private_key.encode(), password=None)
        data = base64.b64decode(cipher_text.encode())
        return private_key.decrypt(
            data,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        ).decode()

    @classmethod
    def create(
        cls,
        report,
        sender,
        recipient,
        message,
        parent=None,
        attachment=None,
        emotion_insight=None,
    ):
        extra = {}
        if emotion_insight:
            extra.update(
                {
                    "emotion": emotion_insight.label
                    if emotion_insight.label in EmotionLabel.values
                    else EmotionLabel.NEUTRAL,
                    "emotion_score": emotion_insight.polarity,
                    "emotion_confidence": emotion_insight.confidence,
                    "risk_level": emotion_insight.risk_level
                    if emotion_insight.risk_level in RiskLevel.values
                    else RiskLevel.NORMAL,
                    "emotion_explanation": emotion_insight.explanation,
                }
            )
        return cls.objects.create(
            report=report,
            sender=sender,
            recipient=recipient,
            parent=parent,
            cipher_for_sender=cls._encrypt_for(sender, message),
            cipher_for_recipient=cls._encrypt_for(recipient, message),
            attachment=attachment,
            **extra,
        )

    def get_body_for(self, user) -> str:
        if user == self.sender:
            return self._decrypt_for(user, self.cipher_for_sender)
        return self._decrypt_for(user, self.cipher_for_recipient)

    def __str__(self) -> str:
        return f"Msg from {self.sender_id} to {self.recipient_id}"

# Counselor Colab Messages
class CollaborationMessage(models.Model):
    """Plain-text collaboration thread between counselors on a case."""

    report = models.ForeignKey(
        Report, related_name="collaboration_messages", on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="collaboration_messages",
        on_delete=models.CASCADE,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["report"], name="collab_msg_report_idx"),
            models.Index(fields=["created_at"], name="collab_msg_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Collab message on report {self.report_id} by {self.sender_id}"


class AdminAlert(models.Model):
    """Alert sent to administrators when a case is resolved."""

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="admin_alerts",
        on_delete=models.CASCADE,
    )
    report = models.ForeignKey(
        Report,
        related_name="admin_alerts",
        on_delete=models.CASCADE,
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"], name="adm_alert_created_idx"),
            models.Index(fields=["admin"],      name="adm_alert_admin_idx"),
            models.Index(fields=["report"],     name="adm_alert_report_idx"),
        ]

    def __str__(self) -> str:
        return f"Alert for report {self.report_id} to admin {self.admin_id}"