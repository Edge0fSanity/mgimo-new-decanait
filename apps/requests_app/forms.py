from django import forms

from .models import StudentRequest


class RequestForm(forms.ModelForm):
    def __init__(self, kind, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Тип задаёт URL, не студент: лишнее поле формы убираем, значение подставит view.
        self.kind = kind
        self.fields["type"].required = False
        if kind == StudentRequest.Type.APPLICATION:
            del self.fields["purpose"]
        else:
            del self.fields["content"]

    class Meta:
        model = StudentRequest
        fields = ["type", "purpose", "content"]
        widgets = {
            "type": forms.HiddenInput,
            "purpose": forms.TextInput(attrs={"size": 40}),
            "content": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        # owner и status здесь не принимаются: их задаёт только сервер.
        if self.kind == StudentRequest.Type.CERTIFICATE and not cleaned.get("purpose"):
            self.add_error("purpose", "Укажите, куда предоставляется справка.")
        if self.kind == StudentRequest.Type.APPLICATION and not cleaned.get("content"):
            self.add_error("content", "Введите текст заявления.")
        return cleaned
