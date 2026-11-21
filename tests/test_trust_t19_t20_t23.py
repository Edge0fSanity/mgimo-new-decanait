"""Тесты T19/T20/T23: слой доверия, пересдача в сроках, задание с пары."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

from apps.academics.admin import ScheduleEntryAdmin
from apps.academics.models import Deadline, Exam, Grade, ScheduleEntry, Subject

from .base import TEST_PASSWORD, BaseTestCase


class TrustBase(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет")
        cls.entry = ScheduleEntry.objects.create(
            group=cls.user_a.student_profile.base_group,
            language_group="",
            subject=cls.subject,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=2),
            room="213",
            teacher="Тестовый преподаватель",
        )


class LastSeenTests(TrustBase):
    def test_login_updates_last_seen_and_session(self):
        profile = self.user_a.student_profile
        self.assertIsNone(profile.last_seen)
        client = self.login(self.user_a)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.last_seen)
        # Прежнее значение (None при первом входе) ушло в сессию для метки «новое».
        self.assertIsNone(client.session.get("last_seen"))

    def test_second_login_keeps_previous_last_seen_in_session(self):
        self.login(self.user_a)
        self.user_a.student_profile.refresh_from_db()
        first = self.user_a.student_profile.last_seen
        client = self.login(self.user_a)
        self.user_a.student_profile.refresh_from_db()
        self.assertGreater(self.user_a.student_profile.last_seen, first)
        self.assertIsNotNone(client.session.get("last_seen"))


class NotEnteredTests(TrustBase):
    def test_not_entered_shown_instead_of_empty_cell(self):
        Grade.objects.create(
            student=self.user_a.student_profile,
            subject=self.subject,
            status=Grade.Status.NOT_ENTERED,
            source_label="Аттестация",
        )
        client = self.login(self.user_a)
        self.assertContains(client.get(reverse("grades")), "Преподаватель ещё не внёс оценку · ожидается")
        self.assertContains(client.get(reverse("grades")), "Эти данные видите только вы")


class RetakeDeadlineTests(TrustBase):
    def setUp(self):
        self.exam = Exam.objects.create(
            student=self.user_a.student_profile,
            subject=self.subject,
            scheduled_at=timezone.now() + timedelta(days=7),
            status=Exam.Status.DEBT,
            retake_at=timezone.now() + timedelta(days=14),
            retake_room="405",
        )
        self.url = reverse("exam_retake_deadline", args=[self.exam.pk])

    def test_post_creates_deadline_idempotently(self):
        client = self.login(self.user_a)
        self.assertEqual(client.get(self.url).status_code, 405)
        response = client.post(self.url)
        self.assertRedirects(response, reverse("grades"))
        deadline = Deadline.objects.get(student=self.user_a.student_profile)
        self.assertEqual(deadline.title, f"Пересдача: {self.subject}")
        self.assertEqual(deadline.due_at, self.exam.retake_at)
        client.post(self.url)
        self.assertEqual(Deadline.objects.count(), 1)

    def test_foreign_exam_is_404(self):
        client = self.login(self.user_b)
        self.assertEqual(client.post(self.url).status_code, 404)
        self.assertEqual(Deadline.objects.count(), 0)


class HomeworkTests(TrustBase):
    def setUp(self):
        # Карточка пары рендерится в виде «Сегодня»: занятие переносим на текущий
        # день (фиксированный час — now()+offset после 22:00 уезжает на завтра).
        self.entry.starts_at = datetime.combine(
            timezone.localdate(), time(21, 0), ZoneInfo("Europe/Moscow")
        )
        self.entry.ends_at = datetime.combine(
            timezone.localdate(), time(22, 0), ZoneInfo("Europe/Moscow")
        )
        self.entry.homework = "Прочитать главу 3, задача 5"
        self.entry.save()
        self.url = reverse("homework_deadline", args=[self.entry.pk])

    def test_homework_visible_in_schedule_card(self):
        client = self.login(self.user_a)
        page = client.get(reverse("schedule"))
        self.assertContains(page, "Задание: Прочитать главу 3, задача 5")
        self.assertContains(page, self.url)

    def test_post_creates_deadline_idempotently(self):
        client = self.login(self.user_a)
        self.assertEqual(client.get(self.url).status_code, 405)
        response = client.post(self.url)
        self.assertRedirects(response, reverse("schedule"))
        deadline = Deadline.objects.get(student=self.user_a.student_profile)
        self.assertEqual(deadline.title, f"Задание: {self.subject} ({self.entry.starts_at:%d.%m})")
        if self.entry.starts_at > timezone.now():
            self.assertEqual(deadline.due_at, self.entry.starts_at)
        else:
            # После 21:00 пара уже прошедшая — срок уходит на конец следующего дня.
            self.assertGreater(deadline.due_at, timezone.now())
        client.post(self.url)
        self.assertEqual(Deadline.objects.count(), 1)

    def test_foreign_language_group_is_404(self):
        # Занятие только языковой группы EN-1: студент B (EN-2) не видит его и получает 404.
        self.entry.language_group = "EN-1"
        self.entry.save()
        client = self.login(self.user_b)
        self.assertEqual(client.post(self.url).status_code, 404)
        self.assertEqual(Deadline.objects.count(), 0)


class UpdatedByTests(TrustBase):
    def test_admin_save_model_fills_updated_by(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        staff = get_user_model().objects.create_user("staff_user", password=TEST_PASSWORD, is_staff=True)
        entry = ScheduleEntry.objects.get(pk=self.entry.pk)
        entry.starts_at = entry.starts_at + timedelta(hours=1)
        request = RequestFactory().post("/")
        request.user = staff
        ScheduleEntryAdmin(ScheduleEntry, admin.site).save_model(request, entry, None, change=True)
        entry.refresh_from_db()
        self.assertEqual(entry.updated_by, staff)
        self.assertIsNotNone(entry.changed_at)
        self.assertEqual(entry.old_room, "213")
