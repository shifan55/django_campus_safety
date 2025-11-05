from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import os
import subprocess
import tempfile
from .models import Report, ReportType, EducationalResource, Quiz, QuizQuestion


def scan_file_for_malware(file):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        for chunk in file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    try:
        result = subprocess.run(["clamscan", "--no-summary", tmp_path], capture_output=True)
        if result.returncode == 1:
            raise ValidationError("Uploaded file failed malware scan")
    except FileNotFoundError:
        raise ValidationError("Malware scanner not available")
    finally:
        os.remove(tmp_path)


class LoginForm(forms.Form):
    """Authentication form with Bootstrap styling and better UX."""
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autocomplete": "username",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "remember_me"}
        ),
        label="Remember me",
    )

class RegistrationForm(forms.ModelForm):
    """User registration form with Bootstrap-friendly widgets."""

    username = forms.CharField(
     widget=forms.TextInput(
         attrs={
             "class": "form-control",
             "placeholder": "Username",
             "autocomplete": "username",
         }
     )
    )
    email = forms.EmailField(
     widget=forms.EmailInput(
         attrs={
             "class": "form-control",
             "placeholder": "University Email",
             "autocomplete": "email",
         }
     )
    )
    password = forms.CharField(
     widget=forms.PasswordInput(
         attrs={"class": "form-control", "placeholder": "Password", "autocomplete": "new-password"}
     )
    )
    password_confirm = forms.CharField(
     label="Confirm password",
     widget=forms.PasswordInput(
         attrs={
             "class": "form-control",
             "placeholder": "Confirm Password",
             "autocomplete": "new-password",
        }
     ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

class AnonymousReportForm(forms.Form):
    incident_type = forms.ChoiceField(
        choices=ReportType.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "class": "form-control", "id": "description"})
    )
    incident_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    location = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "location",
                "placeholder": "Enter or search location",
            }
        ),
    )

    latitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "latitude"})
    )


    longitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "longitude"})
    )

    
    witness_present = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "witness_present"})
    )
    previous_incidents = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "previous_incidents"})
    )
    support_needed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "support_needed"})
    )

    reporter_name = forms.CharField(
        required=False,
        help_text="Optional. Provide if you are comfortable sharing your name.",
        widget=forms.TextInput(attrs={"class": "form-control", "id": "reporter_name"})
    )
    reporter_email = forms.EmailField(
        required=False,
        help_text="Optional. We'll use this only to follow up about your report.",
        widget=forms.EmailInput(attrs={"class": "form-control", "id": "reporter_email"})
    )
    reporter_phone = forms.CharField(
        required=False,
        help_text="Optional. A phone number in case we need more information.",
        widget=forms.TextInput(attrs={"class": "form-control", "id": "reporter_phone"})
    )


class EducationalResourceForm(forms.ModelForm):
    class Meta:
        model = EducationalResource
        fields = ["title", "content", "url", "file", "resource_type", "category", "is_public"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "file": forms.FileInput(attrs={"class": "form-control", "accept": "application/pdf,video/mp4"}),
            "resource_type": forms.Select(attrs={"class": "form-select"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            scan_file_for_malware(file)
        return file

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }


QuizQuestionFormSet = inlineformset_factory(
    Quiz,
    QuizQuestion,
    fields=["text", "option_a", "option_b", "option_c", "option_d", "correct_option"],
    extra=1,
    widgets={
        "text": forms.TextInput(attrs={"class": "form-control"}),
        "option_a": forms.TextInput(attrs={"class": "form-control"}),
        "option_b": forms.TextInput(attrs={"class": "form-control"}),
        "option_c": forms.TextInput(attrs={"class": "form-control"}),
        "option_d": forms.TextInput(attrs={"class": "form-control"}),
        "correct_option": forms.Select(attrs={"class": "form-select"}),
    },
)

class ReportForm(forms.ModelForm):
    
    witness_present = forms.BooleanField(
        required=False,
        label="Were there witnesses present?",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "witness_present"})
    )
    previous_incidents = forms.BooleanField(
        required=False,
        label="Have there been previous similar incidents?",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "previous_incidents"})
    )
    support_needed = forms.BooleanField(
        required=False,
        label="Do you need immediate support?",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "support_needed"})
    )

    # if you use the JS that references these IDs, set them too:
    description = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6, "id": "description"})
    )
    is_anonymous = forms.BooleanField(
        required=False,
        label="Submit this report anonymously",
        widget=forms.HiddenInput(attrs={"id": "is_anonymous"})
    )
    
    class Meta:
        model = Report
        fields = [
            'incident_type', 'incident_date', 'description',
            'location', 'latitude', 'longitude',
            'witness_present', 'previous_incidents', 'support_needed',
            'is_anonymous', 'reporter_name', 'reporter_email', 'reporter_phone'
        ]
        widgets = {
            'incident_type': forms.Select(attrs={
                'class': 'form-select', 'id': 'incident_type', 'required': 'required'
            }),
            'incident_date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control', 'id': 'incident_date', 'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5, 'id': 'description', 'required': 'required'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'location',
                'placeholder': 'Enter location or select on map',
                'required': 'required'
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude'}),
            'reporter_name': forms.HiddenInput(attrs={'id': 'reporter_name'}),
            'reporter_email': forms.HiddenInput(attrs={'id': 'reporter_email'}),
            'reporter_phone': forms.HiddenInput(attrs={'id': 'reporter_phone'}),
            'is_anonymous': forms.HiddenInput(attrs={'id': 'is_anonymous'}),
            'witness_present': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'witness_present'}),
            'previous_incidents': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'previous_incidents'}),
            'support_needed': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'support_needed'}),
        }
        
    
        
    # Make the *fields* required at the form level too (back-end)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['incident_type'].required = True
        self.fields['incident_date'].required = True
        self.fields['description'].required = True

    def clean(self):
        cleaned = super().clean()
        is_anon = cleaned.get('is_anonymous')

        # Enforce server-side as well
        for f in ('incident_type', 'incident_date', 'description'):
            if not cleaned.get(f):
                self.add_error(f, "This field is required.")

        # Only require email when not anonymous
        if not is_anon:
            if not cleaned.get('reporter_email'):
                self.add_error('reporter_email', "Email is required if you are not submitting anonymously.")
        else:
            # Clear contact info for safety if anonymous
            cleaned['reporter_name'] = ''
            cleaned['reporter_email'] = ''
            cleaned['reporter_phone'] = ''

        return cleaned


class MessageForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control chat-input",
                "placeholder": "Type your message...",
            }
        ),
    )
    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,image/*",
                "aria-label": "Attach a file",
            }
        ),
    )
    parent_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "parent_id"}),
    )
    
    def clean(self):
        cleaned = super().clean()
        message = cleaned.get("message", "").strip()
        attachment = cleaned.get("attachment")
        if not message and not attachment:
            raise forms.ValidationError(
                "Please enter a message or attach a file before sending."
            )
        cleaned["message"] = message
        return cleaned