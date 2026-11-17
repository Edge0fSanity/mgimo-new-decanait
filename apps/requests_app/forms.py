from django import forms

from .models import StudentRequest


class RequestForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ["type", "purpose", "content"]
        widgets = {
            "type": forms.RadioSelect,
            "purpose": forms.TextInput(attrs={"size": 40}),
            "content": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        # owner и status здесь не принимаются: их задаёт только сервер.
        if cleaned.get("type") == StudentRequest.Type.CERTIFICATE and not cleaned.get("purpose"):
            self.add_error("purpose", "Укажите, куда предоставляется справка.")
        if cleaned.get("type") == StudentRequest.Type.APPLICATION and not cleaned.get("content"):
            self.add_error("content", "Введите текст заявления.")
        return cleaned
