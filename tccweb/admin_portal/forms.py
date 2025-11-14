from django import forms
from django.apps import apps
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from datetime import date, timedelta


def _apply_bootstrap_classes(form, field_classes):
    """Attach consistent Bootstrap-friendly attributes to form widgets."""

    for name, extra_attrs in field_classes.items():
        field = form.fields.get(name)
        if not field:
            continue
        css_class = field.widget.attrs.get("class", "")
        classes = list(dict.fromkeys(f"{css_class} form-control".split()))
        field.widget.attrs.update({
            "class": " ".join(classes),
            **extra_attrs,
        })

class CounselorCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(
            self,
            {
                "username": {"autocomplete": "username"},
                "email": {"autocomplete": "email"},
                "password1": {"autocomplete": "new-password"},
                "password2": {"autocomplete": "new-password"},
            },
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_staff = True
        user.is_superuser = False
        if commit:
            user.save()
        return user


class AdminCreationForm(UserCreationForm):
    """User creation form that provisions a privileged administrator account."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(
            self,
            {
                "username": {"autocomplete": "username"},
                "email": {"autocomplete": "email"},
                "password1": {"autocomplete": "new-password"},
                "password2": {"autocomplete": "new-password"},
            },
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            return email

        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A user with this email already exists. Please choose another."
            )
        return email

    def save(self, commit=True):
        """Persist a new superuser account that mirrors administrator access."""

        if not commit:
            # Provide a fully configured instance for callers who want to perform
            # additional mutations before saving.
            user = super().save(commit=False)
            user.email = self.cleaned_data["email"]
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            return user

        cleaned = self.cleaned_data
        with transaction.atomic():
            user = User.objects.create_superuser(
                username=cleaned["username"],
                email=cleaned["email"],
                password=cleaned["password1"],
            )
        self.instance = user

        return user


class SubAdminCreationForm(AdminCreationForm):
    """Backward compatible alias for legacy imports expecting a sub-admin form."""

    pass


class ImpersonationForm(forms.Form):
    """Light-weight form that validates the impersonation target."""

    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Select user to impersonate",
        help_text="Only active accounts are available for impersonation.",
    )

    def __init__(self, *args, current_user=None, user_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        queryset = user_queryset or User.objects.filter(is_active=True)
        if current_user is not None:
            queryset = queryset.exclude(pk=current_user.pk)
        self.fields["user"].queryset = queryset
        self.fields["user"].widget.attrs.update({"class": "form-select"})

    def clean_user(self):
        user = self.cleaned_data["user"]
        if self.current_user and user.pk == self.current_user.pk:
            raise forms.ValidationError("You are already signed in as this user.")
        return user
    
class DataExportForm(forms.Form):
    """Capture export filters for compliance-ready data bundles."""

    EXPORT_FORMAT_CHOICES = (
        ("csv", "CSV (spreadsheets)"),
        ("json", "JSON (structured)")
    )

    start_date = forms.DateField(
        required=False,
        label="Start date",
        help_text="First day to include. Leave blank to export from the beginning.",
    )
    end_date = forms.DateField(
        required=False,
        label="End date",
        help_text="Last day to include. Leave blank to export up to today.",
    )
    statuses = forms.MultipleChoiceField(
        required=False,
        label="Report statuses",
        help_text="Limit the export to these case states. All statuses are included when none are selected.",
        widget=forms.SelectMultiple,
    )
    include_case_notes = forms.BooleanField(
        required=False,
        initial=True,
        label="Include counselor case notes",
    )
    include_messages = forms.BooleanField(
        required=False,
        initial=True,
        label="Include secure message metadata",
        help_text="Message bodies remain encrypted; headers and metadata are included for review.",
    )
    include_system_logs = forms.BooleanField(
        required=False,
        initial=True,
        label="Include counselor activity logs",
    )
    include_security_logs = forms.BooleanField(
        required=False,
        initial=True,
        label="Include authentication & permission logs",
    )
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMAT_CHOICES,
        initial="csv",
        label="Data format",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        report_model = apps.get_model("core", "Report")
        status_field = report_model._meta.get_field("status")
        status_choices = list(status_field.choices)
        self.fields["statuses"].choices = status_choices

        today = date.today()
        default_start = today - timedelta(days=30)

        if not self.initial.get("start_date"):
            self.initial["start_date"] = default_start
        if not self.initial.get("end_date"):
            self.initial["end_date"] = today
        if not self.initial.get("statuses"):
            self.initial["statuses"] = [choice[0] for choice in status_choices]

        # Apply Bootstrap-friendly classes and aria attributes.
        for name in ("start_date", "end_date"):
            self.fields[name].widget = forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            )

        self.fields["statuses"].widget.attrs.update({"class": "form-select", "size": "4"})

        for checkbox in (
            "include_case_notes",
            "include_messages",
            "include_system_logs",
            "include_security_logs",
        ):
            self.fields[checkbox].widget.attrs.update({"class": "form-check-input"})

        self.fields["export_format"].widget.attrs.update({"class": "form-check-input"})

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and start > end:
            raise forms.ValidationError("The start date must be on or before the end date.")
        return cleaned