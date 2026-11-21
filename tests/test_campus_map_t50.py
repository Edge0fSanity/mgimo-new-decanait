"""Тесты ревью п.15 (T50): карта корпуса — статичная схема-заглушка."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import ScheduleEntry, Subject

from .base import BaseTestCase


class CampusMapTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        msk = ZoneInfo("Europe/Moscow")
        start = datetime.combine(timezone.localdate() + timedelta(days=1), time(10, 0), msk)
        cls.entry = ScheduleEntry.objects.create(
            group=cls.user_a.student_profile.base_group,
            language_group="",
            subject=Subject.objects.create(title="Тестовый предмет карты"),
            starts_at=start,
            ends_at=start + timedelta(hours=1, minutes=30),
            room="Ауд. 213",
            teacher="Тестовый преподаватель",
        )

    def test_map_page_renders_with_svg(self):
        page = self.login(self.user_a).get(reverse("campus_map"))
        self.assertContains(page, "campus-map.svg")
        self.assertContains(page, "Схема условная")
