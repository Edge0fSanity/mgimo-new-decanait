"""Тесты admin-ввода academics (T6/T9/T10): clean()-валидация и семантика переноса."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib import admin
from django.test import RequestFactory
from django.utils import timezone

from apps.academics.admin import ScheduleEntryAdmin
from apps.academics.models import Deadline, Group, ScheduleEntry, Subject

from .base import BaseTestCase


class ScheduleEntryCleanTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.group = Group.objects.get(code="МЭО-01")
        cls.subject = Subject.objects.create(title="Тестовый предмет clean")

    def test_ends_at_not_before_starts_at(self):
        entry = ScheduleEntry(
            group=self.group, subject=self.subject,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now(), room="Ауд. 1", teacher="Тест",
        )
        with self.assertRaises(ValidationError) as cm:
            entry.full_clean()
        self.assertIn("ends_at", cm.exception.message_dict)


class SubjectWeightsCleanTests(BaseTestCase):
    """Веса блоков заданы все три — сумма должна быть 1, иначе калькуляр врёт."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет весов")

    def test_weights_sum_not_one_rejected(self):
        self.subject.weight_current, self.subject.weight_exam, self.subject.weight_social = Decimal("0.5"), Decimal("0.5"), Decimal("0.1")
        with self.assertRaises(ValidationError):
            self.subject.full_clean()

    def test_weights_sum_one_ok(self):
        self.subject.weight_current, self.subject.weight_exam, self.subject.weight_social = Decimal("0.5"), Decimal("0.4"), Decimal("0.1")
        self.subject.full_clean()  # не бросает

    def test_partial_weights_not_checked(self):
        # Пока заданы не все три — проверка не применяется (схема ещё настраивается).
        self.subject.weight_current, self.subject.weight_exam, self.subject.weight_social = Decimal("0.5"), None, None
        self.subject.full_clean()  # не бросает


class DeadlineCleanTests(BaseTestCase):
    """Фильтры дашборда: (group | student) и due_at >= now — иначе дедлайн никто не увидит."""

    def test_without_group_and_student_rejected(self):
        deadline = Deadline(title="Ничей дедлайн", due_at=timezone.now() + timedelta(days=1))
        with self.assertRaises(ValidationError) as cm:
            deadline.full_clean()
        self.assertNotIn("due_at", cm.exception.message_dict)

    def test_past_due_at_rejected(self):
        group = Group.objects.get(code="МЭО-01")
        deadline = Deadline(group=group, title="Прошедший дедлайн", due_at=timezone.now() - timedelta(days=1))
        with self.assertRaises(ValidationError) as cm:
            deadline.full_clean()
        self.assertIn("due_at", cm.exception.message_dict)

    def test_past_due_at_editable_after_creation(self):
        # Истёкший дедлайн staff должен уметь править (опечатка в названии и т.п.).
        group = Group.objects.get(code="МЭО-01")
        deadline = Deadline.objects.create(group=group, title="Истёкший", due_at=timezone.now() - timedelta(days=1))
        deadline.title = "Истёкший (исправлено)"
        deadline.full_clean()  # не бросает
        deadline.save()


class ScheduleEntryAdminSaveTests(BaseTestCase):
    def test_save_model_fills_transfer_fields_on_change(self):
        group = Group.objects.get(code="МЭО-01")
        subject = Subject.objects.create(title="Тестовый предмет переноса")
        entry = ScheduleEntry.objects.create(
            group=group, subject=subject,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1, minutes=30),
            room="Ауд. 100", teacher="Тест",
        )
        model_admin = ScheduleEntryAdmin(ScheduleEntry, admin.site)
        request = RequestFactory().post("/")

        # Правка без изменения времени/аудитории поля переноса не трогает.
        model_admin.save_model(request, entry, None, change=True)
        entry.refresh_from_db()
        self.assertIsNone(entry.changed_at)

        # Перенос: прежние время/аудитория и момент правки фиксируются.
        old_starts_at = entry.starts_at
        entry.starts_at = old_starts_at + timedelta(hours=2)
        entry.room = "Ауд. 200"
        model_admin.save_model(request, entry, None, change=True)
        entry.refresh_from_db()
        self.assertEqual(entry.old_starts_at, old_starts_at)
        self.assertEqual(entry.old_room, "Ауд. 100")
        self.assertIsNotNone(entry.changed_at)
