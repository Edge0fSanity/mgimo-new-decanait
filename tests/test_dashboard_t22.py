"""Главная: сводка учёбы (оценки/зачёты/задолженности/ближайший экзамен) вместо калькулятора."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Exam, Grade, Subject

from .base import BaseTestCase


class StudySummaryTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        profile = self.user_a.student_profile
        micro = Subject.objects.create(title="Микроэкономика")
        lang = Subject.objects.create(title="Иностранный язык")
        math = Subject.objects.create(title="Математический анализ")
        Grade.objects.create(student=profile, subject=micro, value="5", source_label="Тест")
        Grade.objects.create(
            student=profile, subject=lang, status=Grade.Status.CREDIT, value="зачёт", source_label="Тест"
        )
        Grade.objects.create(student=profile, subject=math, status=Grade.Status.DEBT, source_label="Тест")
        self.exam = Exam.objects.create(
            student=profile, subject=math, scheduled_at=timezone.now() + timedelta(days=7)
        )

    def test_home_shows_study_summary_without_rating(self):
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "Сводка учёбы")
        self.assertContains(page, "Оценок: 1 · зачётов: 1 · задолженностей: 1")
        self.assertContains(page, "Ближайший экзамен")
        self.assertContains(page, reverse("exams"))
        # Процентно-оценочный ярлык из неполного расчёта не показывается нигде.
        self.assertNotContains(page, "summary-percent")
        self.assertNotContains(page, "Сколько нужно набрать")

    def test_home_summary_without_exam(self):
        self.exam.delete()
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "Сводка учёбы")
        self.assertContains(page, "Ближайших экзаменов нет")

    def test_home_summary_is_personal(self):
        # У B нет ни оценок, ни экзаменов — чужой сводки нет.
        page = self.login(self.user_b).get(reverse("home"))
        self.assertContains(page, "Оценок: 0 · зачётов: 0 · задолженностей: 0")
        self.assertNotContains(page, "Микроэкономика")
