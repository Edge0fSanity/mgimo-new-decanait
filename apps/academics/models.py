from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

import re

# Код группы МГИМО: «4МЭО-03-21» = 4 курс, факультет МЭО, 3 академическая группа, 21 языковая.
GROUP_CODE_RE = re.compile(r"^(\d)([А-ЯЁ]+)-(\d{2})-(\d{2})$")


class Group(models.Model):
    code = models.CharField("Код группы", max_length=32, unique=True)
    title = models.CharField("Название", max_length=120)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return self.code

    @property
    def code_description(self):
        """«4МЭО-03-21» → «4МЭО-03-21 · 4 курс · академическая 03 · языковая 21»; неразбираемый код — как есть."""
        m = GROUP_CODE_RE.match(self.code)
        if not m:
            return self.code
        course, _faculty, academic, language = m.groups()
        return f"{self.code} · {course} курс · академическая {academic} · языковая {language}"


class Subject(models.Model):
    title = models.CharField("Дисциплина", max_length=120, unique=True)
    # Веса блоков рейтинга («Положение об академическом рейтинге»); nullable —
    # схема оценивания может быть не задана, тогда рейтинг не считается.
    weight_current = models.DecimalField(
        "Вес текущего контроля", max_digits=3, decimal_places=2, null=True, blank=True
    )
    weight_exam = models.DecimalField(
        "Вес сессии", max_digits=3, decimal_places=2, null=True, blank=True
    )
    weight_social = models.DecimalField(
        "Вес соц. блока", max_digits=3, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Дисциплина"
        verbose_name_plural = "Дисциплины"

    def clean(self):
        # Веса заданы все три — они должны образовывать полный рейтинг (сумма 1),
        # иначе калькулятор показывает всем студентам дисциплины неверные числа.
        weights = (self.weight_current, self.weight_exam, self.weight_social)
        if all(w is not None for w in weights) and abs(sum(map(float, weights)) - 1) > 0.01:
            raise ValidationError("Сумма весов блоков должна быть 1 (сейчас %(sum)s)." % {"sum": round(sum(map(float, weights)), 2)})

    def __str__(self):
        return self.title


def percent_to_mark(percent):
    """Шкала Положения об академическом рейтинге: 0–100% -> оценка."""
    if percent >= 90:
        return "отлично"
    if percent >= 75:
        return "хорошо"
    if percent >= 60:
        return "удовлетворительно"
    return "неудовлетворительно"


class CurrentControlElement(models.Model):
    """Элемент текущего контроля (контрольная/эссэ/коллоквиум). percent null => «не внесено»."""

    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="control_elements"
    )
    title = models.CharField("Элемент контроля", max_length=120)
    percent = models.DecimalField("Процент", max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Элемент текущего контроля"
        verbose_name_plural = "Элементы текущего контроля"
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "title"], name="uniq_control_element")
        ]

    def __str__(self):
        return f"{self.subject}: {self.title}"


class Room(models.Model):
    """Аудитория корпуса; name совпадает со строкой ScheduleEntry.room (ревью п.14)."""

    name = models.CharField("Аудитория", max_length=64, unique=True)

    class Meta:
        verbose_name = "Аудитория"
        verbose_name_plural = "Аудитории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScheduleEntry(models.Model):
    """Занятие. language_group пуст => занятие всей основной группы."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="entries")
    language_group = models.CharField("Языковая группа", max_length=32, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
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
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="schedule_changes",
        verbose_name="Кто изменил",
    )
    homework = models.TextField("Задание с пары", blank=True)

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Расписание"
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["group", "starts_at"])]  # T29: фильтр расписания
        constraints = [
            models.UniqueConstraint(
                fields=["group", "language_group", "subject", "starts_at"],
                name="uniq_schedule_slot",
            )
        ]

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Конец занятия должен быть позже начала."})

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
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    value = models.CharField("Оценка", max_length=32, blank=True)
    percent = models.DecimalField(
        "Процент (сессия)", max_digits=5, decimal_places=2, null=True, blank=True
    )
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
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    scheduled_at = models.DateTimeField("Дата экзамена")
    result = models.CharField("Результат", max_length=32, blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    # Пересдача задолженности (T20): null => дата ещё не назначена.
    retake_at = models.DateTimeField("Дата пересдачи", null=True, blank=True)
    retake_room = models.CharField("Аудитория пересдачи", max_length=64, blank=True)

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
        # T29: фильтры дашборда (group | student) + due_at >= now.
        indexes = [
            models.Index(fields=["group", "due_at"]),
            models.Index(fields=["student", "due_at"]),
        ]

    def clean(self):
        # Фильтры дашборда (apps/dashboard/views.py): (group | student) и due_at >= now.
        if self.group_id is None and self.student_id is None:
            raise ValidationError("Дедлайн должен быть привязан к группе или студенту, иначе его никто не увидит.")
        # Проверка «в прошлом» только при создании: истёкший дедлайн staff должен уметь править.
        if not self.pk and self.due_at and self.due_at < timezone.now():
            raise ValidationError({"due_at": "Срок не может быть в прошлом — такой дедлайн никто не увидит."})

    def __str__(self):
        return self.title
