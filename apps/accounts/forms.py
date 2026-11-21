import io

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from PIL import Image

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


class AvatarForm(forms.ModelForm):
    # T40: фото профиля. Ограничения: JPEG/PNG, до 5 МБ, не меньше 100×100 px.
    class Meta:
        model = StudentProfile
        fields = ["photo"]

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Файл больше 5 МБ.")
        if getattr(photo, "content_type", "") not in ("image/jpeg", "image/png"):
            raise forms.ValidationError("Поддерживаются только JPEG и PNG.")
        # Читаем в память: Image.open не должен владеть стримом аплоада,
        # иначе close() закроет его до сохранения файла (файл сохранится пустым).
        img = Image.open(io.BytesIO(photo.read()))
        try:
            width, height = img.size
        finally:
            img.close()
        photo.seek(0)
        if width < 100 or height < 100:
            raise forms.ValidationError("Минимальный размер — 100×100 пикселей.")
        return photo
