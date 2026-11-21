"""Тесты ревью п.11 (T46): поиск преподавателя по фамилии и его расписание."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import ScheduleEntry, Subject

from .base import BaseTestCase


class TeachersTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет поиска")
        cls.entry = ScheduleEntry.objects.create(
            group=cls.user_a.student_profile.base_group,
            language_group="",
            subject=cls.subject,
            starts_at=timezone.now() + timedelta(hours=2),
            ends_at=timezone.now() + timedelta(hours=3, minutes=30),
            room="213",
            teacher="Кузнецова Ольга",
        )

    def test_search_by_surname_part_finds_teacher(self):
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"q": "узнец"})
        self.assertContains(page, "Кузнецова Ольга")

    def test_selected_teacher_shows_entries(self):
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"teacher": "Кузнецова Ольга"})
        self.assertContains(page, "Кузнецова Ольга — ближайшие занятия")
        self.assertContains(page, "Тестовый предмет поиска")

    def test_empty_query_shows_only_form(self):
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"))
        self.assertContains(page, "Фамилия преподавателя")
        self.assertNotContains(page, "ближайшие занятия")

    def test_schedule_teacher_name_links_to_search(self):
        client = self.login(self.user_a)
        page = client.get(reverse("schedule"))
        self.assertContains(page, "teachers/?teacher=")
