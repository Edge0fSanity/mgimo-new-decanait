from django import forms

from .models import MaintenanceRequest, StudentRequest


class RequestForm(forms.ModelForm):
    def __init__(self, kind, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Тип задаёт URL, не студент: лишнее поле формы убираем, значение подставит view.
        self.kind = kind
        self.fields["type"].required = False
        if kind == StudentRequest.Type.APPLICATION:
            for field in ("subtype", "organization", "purpose"):
                del self.fields[field]
            self.fields["content"].required = True
        else:
            del self.fields["content"]
            # Обязательность на поле: ошибка показывается у конкретного поля до отправки.
            for field in ("subtype", "organization", "purpose", "delivery_method"):
                self.fields[field].required = True
        # Ошибки полей связываются с инпутами: base.css:217 красит [aria-invalid="true"].
        # После конфигурации полей: обращение к errors кэширует валидацию.
        if self.is_bound:
            for field in self.errors or {}:
                if field in self.fields:
                    self.fields[field].widget.attrs["aria-invalid"] = "true"
                    self.fields[field].widget.attrs["aria-describedby"] = f"id_{field}_errors"

    class Meta:
        model = StudentRequest
        fields = ["type", "subtype", "organization", "purpose", "content", "delivery_method"]
        widgets = {
            "type": forms.HiddenInput,
            "organization": forms.TextInput(attrs={"size": 40}),
            "purpose": forms.TextInput(attrs={"size": 40}),
            "content": forms.Textarea(attrs={"rows": 4}),
        }


class MaintenanceForm(forms.ModelForm):
    # T48: заявка на обслуживание кабинета; владелец и статус подставляет view.
    class Meta:
        model = MaintenanceRequest
        fields = ["room", "category", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ошибки полей связываются с инпутами: base.css:217 красит [aria-invalid="true"].
        if self.is_bound:
            for field in self.errors or {}:
                if field in self.fields:
                    self.fields[field].widget.attrs["aria-invalid"] = "true"
                    self.fields[field].widget.attrs["aria-describedby"] = f"id_{field}_errors"
