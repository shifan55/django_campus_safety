from django import forms
from .models import CaseNote, ChatMessage


class CaseNoteForm(forms.ModelForm):
    class Meta:
        model = CaseNote
        fields = ["note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}


class MessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 2})}