"""Тесты ревью п.17–18 (T52/T53): каникулы — блок на главной и баннер за неделю."""
import os
from datetime import date, timedelta
from unittest import mock

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import VacationPeriod

from .base import TEST_PASSWORD, BaseTestCase


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


class SeedVacationsTests(BaseTestCase):
    def seed(self):
        env = {
            "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
            "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
            "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
        }
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
            call_command("seed_demo", verbosity=0)  # повторный seed не дублирует

    def test_seed_winter_only_with_faculty_and_cohort(self):
        # Ревью P1-6: летние даты — неподтверждённый образец, в seed не попадают;
        # у подтверждённых зимних указаны факультет и набор.
        self.seed()
        self.assertFalse(VacationPeriod.objects.filter(title="Летние каникулы 2027").exists())
        winter = VacationPeriod.objects.get(title__startswith="Зимние каникулы 2026/27")
        self.assertEqual(winter.title, "Зимние каникулы 2026/27 (МЭО, набор 2026)")
        self.assertEqual(winter.starts_at, date(2027, 1, 25))
        self.assertEqual(winter.ends_at, date(2027, 1, 31))
        self.assertEqual(VacationPeriod.objects.filter(title__startswith="Зимние").count(), 1)
