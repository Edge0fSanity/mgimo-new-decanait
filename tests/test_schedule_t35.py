"""T35: разметка расписания отдаёт даты занятий и подключает клиентский отсчёт."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

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
            # Фиксированный час сегодня, а не now()+offset: после 22:00 сдвиг
            # уезжает на завтра и пара исчезает из вида «Сегодня».
            starts_at=datetime.combine(timezone.localdate(), time(21, 0), ZoneInfo("Europe/Moscow")),
            ends_at=datetime.combine(timezone.localdate(), time(22, 30), ZoneInfo("Europe/Moscow")),
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
