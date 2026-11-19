from django.conf import settings
from django.db import models, transaction


class DemoDocument(models.Model):
    """Документ-образец: скачивается только владельцем через Django view, не по /media/ URL."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    request = models.ForeignKey(
        "StudentRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    title = models.CharField("Название", max_length=200)
    file = models.FileField(upload_to="documents/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Документ-образец"
        verbose_name_plural = "Документы-образцы"

    def __str__(self):
        return self.title


class StudentRequest(models.Model):
    class Type(models.TextChoices):
        CERTIFICATE = "certificate", "Справка"
        APPLICATION = "application", "Заявление"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Подана"
        IN_PROGRESS = "in_progress", "В обработке"
        READY = "ready", "Готова"
        REJECTED = "rejected", "Отклонена"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requests"
    )
    public_number = models.CharField(max_length=32, unique=True, blank=True)
    type = models.CharField("Тип", max_length=16, choices=Type.choices)
    # Явные колонки вместо произвольного JSON (ARCHITECTURE §4).
    purpose = models.CharField("Куда предоставляется", max_length=200, blank=True)
    content = models.TextField("Текст заявления", blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.SUBMITTED
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-submitted_at"]

    def save(self, *args, **kwargs):
        # public_number строится от pk: первый проход сохраняет, второй присваивает номер.
        # kwargs вызывающего не затираются; номер присваивается и записи без pk-прохода (напр. из admin).
        needs_number = not self.public_number
        with transaction.atomic():
            super().save(*args, **kwargs)
            if needs_number:
                self.public_number = f"{self.get_type_display()[:3].upper()}-{self.submitted_at:%Y}-{self.pk:04d}"
                super().save(update_fields=["public_number"])

    def __str__(self):
        return f"{self.public_number} ({self.get_type_display()})"


class RequestStatusEvent(models.Model):
    """История смены статуса; студент статус не меняет."""

    request = models.ForeignKey(
        StudentRequest, on_delete=models.CASCADE, related_name="status_events"
    )
    from_status = models.CharField(max_length=16, choices=StudentRequest.Status.choices, blank=True)
    to_status = models.CharField(max_length=16, choices=StudentRequest.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Событие статуса"
        verbose_name_plural = "События статусов"
        ordering = ["created_at"]
