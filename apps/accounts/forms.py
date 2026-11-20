from django import forms
from django.contrib.auth import get_user_model


class ProfileForm(forms.ModelForm):
    # Учебные данные (группа, языковая группа, специализация) редактируются только staff — не студентом.
    class Meta:
        model = get_user_model()
        fields = ["email"]
