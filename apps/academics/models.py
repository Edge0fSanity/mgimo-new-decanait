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


class Grade(models.Model):
    """Оценка/зачёт. Никакого выдуманного рейтинга — только записи деканата."""

    class Status(models.TextChoices):
        RECORDED = "recorded", "Оценка выставлена"
        NOT_ENTERED = "not_entered", "Оценка не введена"
        CREDIT = "credit", "Зачёт"
        DEBT = "debt", "Задолженность"

    student = models.ForeignKey(
        "accounts.StudentProfile", on_delete=models.CASCADE, related_name="grades"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    value = models.CharField("Оценка", max_length=32, blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.RECORDED
    )
    source_label = models.CharField("Период/источник", max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "source_label"], name="uniq_grade"
            )
        ]

    def __str__(self):
        return f"{self.student}: {self.subject} — {self.value or self.get_status_display()}"


class Exam(models.Model):
    """Экзамен сессии: дата и результат."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Назначен"
        PASSED = "passed", "Сдан"
        DEBT = "debt", "Задолженность"

    student = models.ForeignKey(
        "accounts.StudentProfile", on_delete=models.CASCADE, related_name="exams"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField("Дата экзамена")
    result = models.CharField("Результат", max_length=32, blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )

    class Meta:
        verbose_name = "Экзамен"
        verbose_name_plural = "Экзамены"
        ordering = ["scheduled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "scheduled_at"], name="uniq_exam"
            )
        ]

    def __str__(self):
        return f"{self.student}: {self.subject} {self.scheduled_at:%d.%m.%Y}"


class Deadline(models.Model):
    """Срок: для группы или персональный (ровно один из двух)."""

    group = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.CASCADE, related_name="deadlines"
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="deadlines",
    )
    title = models.CharField("Что сдать", max_length=200)
    due_at = models.DateTimeField("Срок")

    class Meta:
        verbose_name = "Дедлайн"
        verbose_name_plural = "Дедлайны"
        ordering = ["due_at"]

    def __str__(self):
        return self.title
