from django.db import models


class Group(models.Model):
    code = models.CharField("Код группы", max_length=32, unique=True)
    title = models.CharField("Название", max_length=120)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return self.code


class Subject(models.Model):
    title = models.CharField("Дисциплина", max_length=120, unique=True)

    class Meta:
        verbose_name = "Дисциплина"
        verbose_name_plural = "Дисциплины"

    def __str__(self):
        return self.title


class ScheduleEntry(models.Model):
    """Занятие. language_group пуст => занятие всей основной группы."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="entries")
    language_group = models.CharField("Языковая группа", max_length=32, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    starts_at = models.DateTimeField("Начало")
    ends_at = models.DateTimeField("Конец")
    room = models.CharField("Аудитория", max_length=64)
    teacher = models.CharField("Преподаватель", max_length=120)
    # Перенос: прежние значения и заметка об изменении.
    old_starts_at = models.DateTimeField(null=True, blank=True)
    old_room = models.CharField(max_length=64, blank=True)
    change_reason = models.CharField(max_length=200, blank=True)
    change_source_role = models.CharField(max_length=32, blank=True)
    changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Расписание"
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "language_group", "subject", "starts_at"],
                name="uniq_schedule_slot",
            )
        ]

    def __str__(self):
        return f"{self.subject} {self.starts_at:%d.%m %H:%M}"
