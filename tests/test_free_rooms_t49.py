"""Тесты ревью п.14 (T49) и P0-3: аудитории без занятий по расписанию."""
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

    def test_page_renamed(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"date": self.day, "start": "12:30", "end": "13:00"})
        self.assertContains(page, "Аудитории без занятий по расписанию")
        self.assertNotContains(page, "Свободные аудитории")

    def test_busy_room_excluded_free_listed(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"date": self.day, "start": "12:30", "end": "13:00"})
        self.assertNotContains(page, "Ауд. 301")
        self.assertContains(page, "Ауд. 999")

    def test_outside_interval_room_is_free(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"date": self.day, "start": "14:00", "end": "15:00"})
        self.assertContains(page, "Ауд. 301")

    def test_no_schedule_date_shows_message(self):
        client = self.login(self.user_a)
        far = (timezone.localdate() + timedelta(days=30)).isoformat()
        page = client.get(reverse("free_rooms"), {"date": far, "start": "12:30", "end": "13:00"})
        self.assertContains(page, "Расписание на эту дату не загружено")
        self.assertNotContains(page, "Ауд. 999")

    def test_empty_room_directory_shows_message(self):
        client = self.login(self.user_a)
        Room.objects.all().delete()
        try:
            page = client.get(reverse("free_rooms"), {"date": self.day, "start": "12:30", "end": "13:00"})
        finally:
            Room.objects.get_or_create(name="Ауд. 301")
            Room.objects.get_or_create(name="Ауд. 999")
        self.assertContains(page, "Справочник аудиторий пока пуст")
        self.assertNotContains(page, "Ауд. 301")

    def test_all_busy_shows_no_suitable_rooms(self):
        client = self.login(self.user_a)
        msk = ZoneInfo("Europe/Moscow")
        start = datetime.combine(timezone.localdate() + timedelta(days=1), time(12, 0), msk)
        day = start.date().isoformat()
        subjects = [self.subject, Subject.objects.create(title="Тестовый предмет аудиторий 2")]
        for room, subject in zip(("Ауд. 301", "Ауд. 999"), subjects):
            ScheduleEntry.objects.create(
                group=self.user_a.student_profile.base_group,
                language_group="",
                subject=subject,
                starts_at=start,
                ends_at=start + timedelta(hours=1, minutes=30),
                room=room,
                teacher="Тестовый преподаватель",
            )
        page = client.get(reverse("free_rooms"), {"date": day, "start": "12:30", "end": "13:00"})
        self.assertContains(page, "Нет подходящих аудиторий")
        self.assertNotContains(page, "Ауд. 301")

    def test_invalid_interval_shows_error(self):
        client = self.login(self.user_a)
        page = client.get(reverse("free_rooms"), {"start": "15:00", "end": "14:00"})
        self.assertContains(page, "Конец интервала должен быть позже начала")
