from django import forms
from .models import CaseNote


class CaseNoteForm(forms.ModelForm):
    class Meta:
        model = CaseNote
        fields = ["note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
   
