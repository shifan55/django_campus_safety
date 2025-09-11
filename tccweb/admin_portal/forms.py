from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CounselorCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_staff = True
        user.is_superuser = False
        if commit:
            user.save()
        return user 