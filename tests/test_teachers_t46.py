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

    def test_search_lowercase_finds_cyrillic_teacher(self):
        """P1-5: «смирнов» находит «проф. Смирнов Пётр» (icontains в SQLite регистрозависим)."""
        ScheduleEntry.objects.create(
            group=self.user_a.student_profile.base_group,
            language_group="",
            subject=self.subject,
            starts_at=timezone.now() + timedelta(hours=4),
            ends_at=timezone.now() + timedelta(hours=5, minutes=30),
            room="214",
            teacher="проф. Смирнов Пётр",
        )
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"q": "смирнов"})
        self.assertContains(page, "проф. Смирнов Пётр")

    def test_finished_today_entries_excluded_ongoing_shown(self):
        """P1-5: завершившиеся сегодня пары не показываются, идущая сейчас — видна."""
        now = timezone.now()
        finished = ScheduleEntry.objects.create(
            group=self.user_a.student_profile.base_group,
            language_group="",
            subject=Subject.objects.create(title="Завершённый предмет"),
            starts_at=now - timedelta(hours=3),
            ends_at=now - timedelta(hours=1, minutes=30),
            room="215",
            teacher="Кузнецова Ольга",
        )
        ongoing = ScheduleEntry.objects.create(
            group=self.user_a.student_profile.base_group,
            language_group="",
            subject=Subject.objects.create(title="Идущий предмет"),
            starts_at=now - timedelta(minutes=30),
            ends_at=now + timedelta(minutes=80),
            room="216",
            teacher="Кузнецова Ольга",
        )
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"teacher": "Кузнецова Ольга"})
        self.assertNotContains(page, finished.subject.title)
        self.assertContains(page, ongoing.subject.title)

    def test_back_link_preserves_week(self):
        """P1-5: ссылка «К расписанию» возвращает на выбранную неделю."""
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"week_of": "2026-12-28"})
        self.assertContains(page, "view=week&amp;week_of=2026-12-28")
        self.assertNotContains(page, "week_of=2026-12-28&amp;")

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
