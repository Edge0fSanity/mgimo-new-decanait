from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    display_name = models.CharField("ФИО", max_length=120)
    faculty = models.CharField("Факультет", max_length=120)
    program = models.CharField("Направление", max_length=120)
    year = models.PositiveSmallIntegerField("Курс")
    base_group = models.ForeignKey(
        "academics.Group", on_delete=models.PROTECT, related_name="students"
    )
    language_group = models.CharField("Языковая группа", max_length=32)
    specialization = models.CharField("Специализация", max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Предыдущий вход (T19.4): обновляется при входе, прежнее значение уходит в сессию.
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"

    def __str__(self):
        return self.display_name
