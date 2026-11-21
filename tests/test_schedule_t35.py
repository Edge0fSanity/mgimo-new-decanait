"""T35: разметка расписания отдаёт даты занятий и подключает клиентский отсчёт."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import ScheduleEntry, Subject

from .base import BaseTestCase


class ScheduleCountdownTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет")
        cls.entry = ScheduleEntry.objects.create(
            group=cls.user_a.student_profile.base_group,
            language_group="",
            subject=cls.subject,
            starts_at=timezone.now() + timedelta(hours=2),
            ends_at=timezone.now() + timedelta(hours=3, minutes=30),
            room="213",
            teacher="Тестовый преподаватель",
        )

    def test_entry_has_machine_readable_dates_and_script(self):
        client = self.login(self.user_a)
        page = client.get(reverse("schedule"))
        self.assertContains(
            page, 'data-starts-at="' + timezone.localtime(self.entry.starts_at).isoformat()
        )
        self.assertContains(
            page, 'data-ends-at="' + timezone.localtime(self.entry.ends_at).isoformat()
        )
        self.assertContains(page, "schedule-countdown.js")

    def test_entry_card_has_no_map_link(self):
        client = self.login(self.user_a)
        page = client.get(reverse("schedule"))
        self.assertNotContains(page, reverse("campus_map"))
        self.assertNotContains(page, ">карта</a>")
