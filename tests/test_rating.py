"""Тесты рейтинга (T15–T17): шкала, калькулятор, пустые клетки, IDOR, seed."""
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import reverse

from apps.academics.models import CurrentControlElement, Grade, Subject, percent_to_mark

from .base import TEST_PASSWORD, BaseTestCase


class ScaleTests(SimpleTestCase):
    def test_boundaries(self):
        # Границы Положения: 90/75/60 включительно, ниже — следующий уровень.
        self.assertEqual(percent_to_mark(100), "отлично")
        self.assertEqual(percent_to_mark(90), "отлично")
        self.assertEqual(percent_to_mark(89.99), "хорошо")
        self.assertEqual(percent_to_mark(75), "хорошо")
        self.assertEqual(percent_to_mark(74.99), "удовлетворительно")
        self.assertEqual(percent_to_mark(60), "удовлетворительно")
        self.assertEqual(percent_to_mark(59.99), "неудовлетворительно")
        self.assertEqual(percent_to_mark(0), "неудовлетворительно")


class CalculatorBase(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(
            title="Рейтинговый предмет",
            weight_current="0.40", weight_exam="0.50", weight_social="0.10",
        )
        CurrentControlElement.objects.create(subject=cls.subject, title="Контрольная", percent="85")
        CurrentControlElement.objects.create(subject=cls.subject, title="Эссэ")  # «не внесено»
        Grade.objects.create(
            student=cls.user_a.student_profile, subject=cls.subject, value="4", source_label="Тест"
        )
        cls.plain_subject = Subject.objects.create(title="Предмет без схемы")
        Grade.objects.create(
            student=cls.user_a.student_profile, subject=cls.plain_subject, source_label="Тест"
        )
        cls.foreign_subject = Subject.objects.create(
            title="Чужой предмет", weight_current="0.40", weight_exam="0.50", weight_social="0.10"
        )
        Grade.objects.create(
            student=cls.user_b.student_profile, subject=cls.foreign_subject, source_label="Тест"
        )
        cls.credit_subject = Subject.objects.create(title="Зачётный предмет")
        Grade.objects.create(
            student=cls.user_a.student_profile, subject=cls.credit_subject,
            status=Grade.Status.CREDIT, value="зачёт", source_label="Зачёт",
        )


class CalculatorTests(CalculatorBase):
    def test_targets_reachable(self):
        # Текущее среднее 85 => база 0.4*85 + 0.1*100 = 44; цели (60/75/90) достижимы.
        client = self.login(self.user_a)
        page = client.get(reverse("subject_detail", args=[self.subject.pk]))
        self.assertContains(page, "не меньше 32%")
        self.assertContains(page, "не меньше 62%")
        self.assertContains(page, "не меньше 92%")

    def test_target_unreachable(self):
        # Низкий текущий контроль: отлично и хорошо недостижимы, честный максимум.
        CurrentControlElement.objects.create(subject=self.foreign_subject, title="Контрольная", percent="10")
        client = self.login(self.user_b)
        page = client.get(reverse("subject_detail", args=[self.foreign_subject.pk]))
        self.assertContains(page, "недостижимо, максимум — удовлетворительно")
        self.assertContains(page, "не меньше 92%")  # до «зачёта» ещё можно успеть

    def test_empty_cell_is_not_zero(self):
        client = self.login(self.user_a)
        page = client.get(reverse("subject_detail", args=[self.subject.pk]))
        self.assertContains(page, "Не внесено")
        self.assertContains(page, "Не внесено оценок — 1")

    def test_no_weights_shows_only_accumulated(self):
        client = self.login(self.user_a)
        page = client.get(reverse("subject_detail", args=[self.plain_subject.pk]))
        self.assertContains(page, "Схема оценивания не задана")
        self.assertNotContains(page, "Посчитать итог")

    def test_slider_computes_final(self):
        client = self.login(self.user_a)
        page = client.get(reverse("subject_detail", args=[self.subject.pk]), {"n": "80"})
        # 44 + 0.5*80 = 84 => хорошо; ярлык — только как гипотетический расчёт.
        self.assertContains(page, "При 80% на экзамене: 84% · хорошо (гипотетический расчёт)")

    def test_calculator_shows_assumptions(self):
        client = self.login(self.user_a)
        page = client.get(reverse("subject_detail", args=[self.subject.pk]))
        self.assertContains(page, "Расчёт при заданных баллах")
        self.assertContains(page, "Текущий контроль — общий по дисциплине")
        self.assertContains(page, "Социальный блок считается зачтённым (100%)")
        self.assertContains(page, "Экзамен ещё не сдан — расчёт гипотетический")

    def test_idor_other_students_subject_404(self):
        client = self.login(self.user_a)
        self.assertEqual(client.get(reverse("subject_detail", args=[self.foreign_subject.pk])).status_code, 404)
        client = self.login(self.user_b)
        self.assertEqual(client.get(reverse("subject_detail", args=[self.subject.pk])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("subject_detail", args=[self.subject.pk])).status_code, 302)


class GradesSummaryTests(CalculatorBase):
    def test_summary_and_card_states(self):
        client = self.login(self.user_a)
        page = client.get(reverse("grades"))
        self.assertContains(page, "Сводка учёбы")
        self.assertContains(page, "выставленных оценок")
        self.assertContains(page, "Зачёт получен")
        # Процентно-оценочный ярлык из неполного расчёта не показывается.
        self.assertNotContains(page, "grades-summary-percent")
        self.assertNotContains(page, "· отлично")
        # Карточка дисциплины: только фактические данные (внесено 1 из 2 элементов).
        self.assertContains(page, "Текущий контроль: внесено 1 из 2")
        self.assertNotContains(page, "Рейтинговый предмет 85%")


class SeedRatingTests(BaseTestCase):
    def test_seed_creates_weights_and_elements_idempotently(self):
        env = {
            "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
            "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
            "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
        }
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
            count = CurrentControlElement.objects.count()
            call_command("seed_demo", verbosity=0)
        self.assertEqual(CurrentControlElement.objects.count(), count)
        micro = Subject.objects.get(title="Микроэкономика")
        self.assertEqual(str(micro.weight_current), "0.40")
        self.assertEqual(str(micro.weight_exam), "0.50")
        self.assertEqual(str(micro.weight_social), "0.10")
        self.assertTrue(
            CurrentControlElement.objects.filter(subject__title="Математический анализ", percent__isnull=True).exists()
        )


class TwoStudentsGradesTests(BaseTestCase):
    def test_two_students_see_different_recorded_grades(self):
        # Seed: у demo_a по «Микроэкономике» 5, у demo_b — 4 (одна дисциплина).
        env = {
            "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
            "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
            "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
        }
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
        user_model = get_user_model()
        user_a = user_model.objects.get(username="demo_a")
        user_b = user_model.objects.get(username="demo_b")
        page_a = self.login(user_a).get(reverse("grades"))
        self.assertContains(page_a, "Оценка 5 (итог)")
        page_b = self.login(user_b).get(reverse("grades"))
        self.assertContains(page_b, "Оценка 4 (итог)")
        self.assertNotContains(page_b, "Оценка 5 (итог)")
        # Ни у одного на учёбе и главной нет процентно-оценочного ярлыка из неполного расчёта.
        for page in (page_a, page_b):
            self.assertNotContains(page, "grades-summary-percent")
            self.assertNotContains(page, "· отлично")
        self.assertNotContains(self.login(user_a).get(reverse("home")), "summary-percent")
        self.assertNotContains(self.login(user_b).get(reverse("home")), "summary-percent")
