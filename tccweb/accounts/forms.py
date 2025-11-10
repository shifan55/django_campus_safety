"""Forms to manage user profile updates and validation."""
from __future__ import annotations

from typing import Iterable

from django import forms
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()

_ALLOWED_AVATAR_TYPES: Iterable[str] = (
    "image/jpeg",
    "image/png",
    "image/gif",
)
_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


class ProfileForm(forms.ModelForm):
    """Form for editing a user's profile information."""

    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "phone",
            "location",
            "timezone",
            "bio",
            "avatar",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        profile = self.instance
        if self.user is None and profile is not None:
            self.user = profile.user
        if self.user:
            self.fields["email"].initial = self.user.email
            if not self.initial.get("full_name") and self.user.get_full_name():
                self.initial["full_name"] = self.user.get_full_name()
        self.fields["avatar"].required = False
        self.fields["avatar"].help_text = "PNG, JPG, or GIF up to 5 MB."
        for name in ["full_name", "email", "phone", "location", "timezone", "bio"]:
            field = self.fields.get(name)
            if field is None:
                continue
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css_class + " form-control").strip()
        avatar_widget = self.fields["avatar"].widget
        avatar_widget.attrs.update(
            {
                "class": (avatar_widget.attrs.get("class", "") + " form-control").strip(),
                "accept": ",".join(_ALLOWED_AVATAR_TYPES),
                "data-avatar-input": "true",
                "data-avatar-allowed": ",".join(_ALLOWED_AVATAR_TYPES),
                "data-avatar-max-size": str(_MAX_AVATAR_SIZE),
            }
        )
        self.fields["full_name"].widget.attrs.setdefault("autocomplete", "name")
        self.fields["email"].widget.attrs.setdefault("autocomplete", "email")
        self.fields["phone"].widget.attrs.setdefault("autocomplete", "tel")
        self.fields["location"].widget.attrs.setdefault("autocomplete", "address-level2")
        self.fields["timezone"].widget.attrs.setdefault("placeholder", "e.g., America/New_York")
        self.fields["bio"].widget.attrs.setdefault("aria-describedby", "bio-hint")
        for name, field in self.fields.items():
            if name in self.errors:
                field.widget.attrs["class"] = (
                    field.widget.attrs.get("class", "") + " is-invalid"
                ).strip()

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name", "")
        return full_name.strip()

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar
        content_type = getattr(avatar, "content_type", None)
        if content_type not in _ALLOWED_AVATAR_TYPES:
            raise forms.ValidationError("Please upload a JPG, PNG, or GIF image.")
        if avatar.size and avatar.size > _MAX_AVATAR_SIZE:
            raise forms.ValidationError("Avatar must be smaller than 5 MB.")
        return avatar

    def save(self, commit: bool = True) -> Profile:
        profile: Profile = super().save(commit=False)
        if self.user is None:
            self.user = profile.user
        email = self.cleaned_data.get("email")
        full_name = self.cleaned_data.get("full_name", "").strip()
        if self.user:
            user_updates: list[str] = []
            if email is not None and email != self.user.email:
                self.user.email = email
                user_updates.append("email")
            if full_name:
                parts = [part for part in full_name.split(" ") if part]
                if parts:
                    first_name = parts[0]
                    last_name = " ".join(parts[1:])
                    if first_name != self.user.first_name:
                        self.user.first_name = first_name
                        user_updates.append("first_name")
                    if last_name != self.user.last_name:
                        self.user.last_name = last_name
                        user_updates.append("last_name")
            if commit and user_updates:
                self.user.save(update_fields=user_updates)
        if commit:
            profile.save()
            self.save_m2m()
        return profile