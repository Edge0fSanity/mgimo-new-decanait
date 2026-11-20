"""Тесты admin-ввода academics (T6/T9/T10): clean()-валидация и семантика переноса."""
from datetime import timedelta

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
