"""P0-2: перенос и «Добавить в дедлайны» в неделю экспертизы 23–27.11.2026."""
import os
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Deadline, ScheduleEntry, Subject

from .base import TEST_PASSWORD, BaseTestCase

SEED_ENV = {
    "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
    "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
    "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
}


class ExpertiseWeekSeedTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        with mock.patch.dict(os.environ, SEED_ENV):
            call_command("seed_demo", verbosity=0)
            call_command("seed_demo", verbosity=0)  # повторный seed не дублирует

    def test_seed_creates_single_rescheduled_entry_in_expertise_week(self):
        starts = timezone.make_aware(datetime(2026, 11, 26, 15, 0))
        entries = ScheduleEntry.objects.filter(starts_at=starts)
        self.assertEqual(entries.count(), 1)
        entry = entries.get()
        self.assertIsNotNone(entry.old_starts_at)
        self.assertEqual(entry.old_room, "Ауд. 112")
        self.assertTrue(entry.homework)

    def test_expertise_week_page_shows_badge_and_button(self):
        demo_a = get_user_model().objects.get(username="demo_a")
        client = self.login(demo_a)
        page = client.get("/schedule/?view=week&week_of=2026-11-23")
        self.assertContains(page, "Перенос")
        self.assertContains(page, "Добавить в дедлайны")


class HomeworkDeadlineWeekTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет")

    def _make_entry(self, starts_at):
        return ScheduleEntry.objects.create(
            group=self.user_a.student_profile.base_group,
            language_group="",
            subject=self.subject,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1, minutes=30),
            room="213",
            teacher="Тестовый преподаватель",
            homework="Прочитать главу 3",
        )

    def test_post_keeps_selected_week_and_shows_message_with_link(self):
        entry = self._make_entry(timezone.now() + timedelta(days=3))
        url = reverse("homework_deadline", args=[entry.pk])
        client = self.login(self.user_a)
        response = client.post(url, {"week_of": "2026-11-23"}, follow=True)
        self.assertRedirects(response, "/schedule/?view=week&week_of=2026-11-23")
        self.assertContains(response, "Добавлено в дедлайны")
        self.assertContains(response, reverse("deadlines"))
        self.assertContains(response, 'value="2026-11-23"')

    def test_past_entry_gets_future_deadline(self):
        entry = self._make_entry(timezone.now() - timedelta(days=7))
        url = reverse("homework_deadline", args=[entry.pk])
        client = self.login(self.user_a)
        client.post(url)
        deadline = Deadline.objects.get(student=self.user_a.student_profile)
        self.assertGreater(deadline.due_at, timezone.now())

    def test_second_post_creates_no_duplicate(self):
        entry = self._make_entry(timezone.now() - timedelta(days=7))
        url = reverse("homework_deadline", args=[entry.pk])
        client = self.login(self.user_a)
        client.post(url, {"week_of": "2026-11-23"})
        client.post(url, {"week_of": "2026-11-23"})
        self.assertEqual(Deadline.objects.filter(student=self.user_a.student_profile).count(), 1)
