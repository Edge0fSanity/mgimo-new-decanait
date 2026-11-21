from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import StudentProfile


class LoginForm(AuthenticationForm):
    # Ошибки полей связываются с инпутами: base.css:217 красит [aria-invalid="true"].
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            for field in self.errors or {}:
                if field in self.fields:
                    self.fields[field].widget.attrs["aria-invalid"] = "true"
                    self.fields[field].widget.attrs["aria-describedby"] = f"id_{field}_errors"


class ProfileForm(forms.ModelForm):
    # Учебные данные (группа, языковая группа, специализация) редактируются только staff — не студентом.
    class Meta:
        model = get_user_model()
        fields = ["email"]
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}


class ThemeForm(forms.ModelForm):
    # T25: выбор оформления сохраняется в профиле студента.
    class Meta:
        model = StudentProfile
        fields = ["theme"]
