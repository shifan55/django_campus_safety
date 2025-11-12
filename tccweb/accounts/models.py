"""Profile models and signal handlers for campus safety users."""
from __future__ import annotations

import os
import uuid
from typing import Optional

from django.conf import settings
from django.core.files.base import File
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver


def avatar_upload_to(instance: "Profile", filename: str) -> str:
    """Generate a stable but unique avatar path for a user."""
    base, ext = os.path.splitext(filename)
    ext = ext.lower() or ".jpg"
    return f"avatars/user_{instance.user_id}/{uuid.uuid4().hex}{ext}"


class Profile(models.Model):
    """Additional profile data that augments the built-in user model."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
    )
    # 2FA
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text=(
            "True when the account has completed the project-specific two-factor "
            "authentication setup process."
        ),
    )
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"], name="profile_user_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - representational helper
        return f"Profile<{self.user_id}>"

    @property
    def email(self) -> str:
        return getattr(self.user, "email", "")

    @property
    def avatar_url(self) -> str:
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:  # pragma: no cover - storage misconfiguration fallback
                return ""
        return ""

    @property
    def role(self) -> str:
        return getattr(self, "_role_override", getattr(self.user, "role", ""))

    def set_role(self, value: str) -> None:
        """Set a transient role label for template rendering."""
        self._role_override = value


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """Guarantee every user has an attached profile row."""
    if created:
        Profile.objects.create(user=instance)


@receiver(pre_save, sender=Profile)
def delete_old_avatar_on_change(sender, instance: Profile, **kwargs):
    """Remove the previous avatar from storage when a new one is uploaded."""
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:  # pragma: no cover - defensive guard
        return
    old_avatar: Optional[File] = previous.avatar
    if old_avatar and instance.avatar and old_avatar.name != instance.avatar.name:
        storage = old_avatar.storage
        if storage.exists(old_avatar.name):
            storage.delete(old_avatar.name)


@receiver(post_delete, sender=Profile)
def delete_avatar_file(sender, instance: Profile, **kwargs):
    """Clean up avatar files when a profile row is removed."""
    avatar = instance.avatar
    if avatar:
        storage = avatar.storage
        if storage.exists(avatar.name):
            storage.delete(avatar.name)