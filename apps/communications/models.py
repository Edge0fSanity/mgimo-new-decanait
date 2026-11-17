from django.conf import settings
from django.db import models


class Announcement(models.Model):
    """Объявление деканата: общее или для группы."""

    class Audience(models.TextChoices):
        ALL = "all", "Всем студентам"
        GROUP = "group", "Группе"

    title = models.CharField("Заголовок", max_length=200)
    body = models.TextField("Текст")
    audience = models.CharField(
        "Аудитория", max_length=8, choices=Audience.choices, default=Audience.ALL
    )
    group = models.ForeignKey(
        "academics.Group", null=True, blank=True, on_delete=models.CASCADE, related_name="announcements"
    )
    published_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class Notification(models.Model):
    """Личное уведомление студента; read_at меняет только сервер для получателя."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField("Тип", max_length=16)  # status / announcement / deadline
    title = models.CharField("Заголовок", max_length=200)
    target_url = models.CharField("Ссылка", max_length=200, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
