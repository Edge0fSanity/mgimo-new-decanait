from django import forms
from django.contrib.auth import get_user_model

from .models import StudentProfile


class ProfileForm(forms.ModelForm):
    # Учебные данные (группа, языковая группа, специализация) редактируются только staff — не студентом.
    class Meta:
        model = get_user_model()
        fields = ["email"]


class ThemeForm(forms.ModelForm):
    # T25: выбор оформления сохраняется в профиле студента.
    class Meta:
        model = StudentProfile
        fields = ["theme"]
