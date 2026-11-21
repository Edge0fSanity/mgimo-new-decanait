"""Тесты ревью п.17–18 (T52/T53): каникулы — блок на главной и баннер за неделю."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import VacationPeriod

from .base import BaseTestCase


class VacationTests(BaseTestCase):
    def add(self, start_offset, title="Каникулы"):
        today = timezone.localdate()
        return VacationPeriod.objects.create(
            title=title, starts_at=today + timedelta(days=start_offset), ends_at=today + timedelta(days=start_offset + 7)
        )

    def test_banner_shows_within_week(self):
        self.add(5, "Зимние каникулы")
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "vacation-banner")
        self.assertContains(page, "Зимние каникулы: каникулы с")

    def test_no_banner_eight_days_out(self):
        self.add(8, "Далёкие каникулы")
        page = self.login(self.user_a).get(reverse("home"))
        self.assertNotContains(page, "vacation-banner")
        self.assertContains(page, "Далёкие каникулы")  # блок «Ближайшие каникулы» виден всегда

    def test_banner_during_vacation(self):
        self.add(-2, "Текущие каникулы")
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "каникулы идут до")

    def test_empty_state_without_periods(self):
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "Даты каникул не заданы")
