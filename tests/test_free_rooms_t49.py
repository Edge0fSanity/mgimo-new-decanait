"""Тесты ревью п.14 (T49): сервис поиска свободной аудитории."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Room, ScheduleEntry, Subject

from .base import BaseTestCase


class FreeRoomsTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет аудиторий")
        Room.objects.get_or_create(name="Ауд. 301")
        Room.objects.get_or_create(name="Ауд. 999")
        msk = ZoneInfo("Europe/Moscow")
        start = datetime.combine(timezone.localdate(), time(12, 0), msk)
        cls.day = start.date().isoformat()
        cls.entry = ScheduleEntry.objects.create(
            group=cls.user_a.student_profile.base_group,
            language_group="",
            subject=cls.subject,
            starts_at=start,
            ends_at=start + timedelta(hours=1, minutes=30),
            room="Ауд. 301",
            teacher="Тестовый преподаватель",
        )

    def test_busy_room_excluded_free_listed(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"date": self.day, "start": "12:30", "end": "13:00"})
        self.assertNotContains(page, "Ауд. 301")
        self.assertContains(page, "Ауд. 999")

    def test_outside_interval_room_is_free(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"date": self.day, "start": "14:00", "end": "15:00"})
        self.assertContains(page, "Ауд. 301")

    def test_invalid_interval_shows_error(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"start": "15:00", "end": "14:00"})
        self.assertContains(page, "Конец интервала должен быть позже начала")
