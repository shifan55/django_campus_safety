from django import forms
from django.contrib.auth import get_user_model
from .models import CaseNote


class CaseNoteForm(forms.ModelForm):
    class Meta:
        model = CaseNote
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control"})
        }
   
# Counselor Collaboration
class CounselorInvitationForm(forms.Form):
    invitee = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Collaborating counselor",
    )

    def __init__(self, *args, **kwargs):
        requester = kwargs.pop("requester", None)
        report = kwargs.pop("report", None)
        super().__init__(*args, **kwargs)
        qs = get_user_model().objects.filter(is_active=True, is_staff=True)
        if requester:
            qs = qs.exclude(pk=requester.pk)
        if report:
            exclude_ids = [
                report.assigned_to_id,
                getattr(report, "collaborating_counselor_id", None),
                getattr(report, "invited_counselor_id", None),
            ]
            qs = qs.exclude(pk__in=[pk for pk in exclude_ids if pk])
        self.fields["invitee"].queryset = qs.order_by("first_name", "last_name")


class CollaborationMessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Share an update with your collaborating counselor",
            }
        ),
        label="Message",
    )

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        if not content:
            raise forms.ValidationError("Please enter a message before sending.")
        return content