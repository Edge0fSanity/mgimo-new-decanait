"""T22: строка калькулятора «до „хорошо“ нужно N%» на экране «Сегодня»."""
from django.urls import reverse

from apps.academics.models import CurrentControlElement, Grade, Subject

from .base import BaseTestCase


class RatingHintTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.subject = Subject.objects.create(
            title="Микроэкономика", weight_current="0.40", weight_exam="0.50", weight_social="0.10"
        )
        CurrentControlElement.objects.create(subject=self.subject, title="Контрольная работа", percent="85")
        CurrentControlElement.objects.create(subject=self.subject, title="Эссэ", percent="78")

    def test_hint_shown_with_percent_and_link(self):
        # 0.4*81.5 + 0.1*100 = 42.6; (75 - 42.6) / 0.5 = 64.8 -> 65
        Grade.objects.create(
            student=self.user_a.student_profile, subject=self.subject, value="5", source_label="Тест"
        )
        client = self.login(self.user_a)
        page = client.get(reverse("home"))
        self.assertContains(page, "До «хорошо» по Микроэкономика на экзамене нужно 65%")
        self.assertContains(page, reverse("subject_detail", args=[self.subject.pk]))

        # У B нет оценки по дисциплине — чужой строки нет (и ссылка не 404).
        client = self.login(self.user_b)
        self.assertNotContains(client.get(reverse("home")), "на экзамене нужно")

    def test_hint_absent_without_data(self):
        # Веса заданы, но элементы текущего контроля не внесены.
        client = self.login(self.user_a)
        self.assertNotContains(client.get(reverse("home")), "на экзамене нужно")

        self.subject.weight_current = None
        self.subject.weight_exam = None
        self.subject.save(update_fields=["weight_current", "weight_exam"])
        CurrentControlElement.objects.filter(subject=self.subject).update(percent="85")
        self.assertNotContains(client.get(reverse("home")), "на экзамене нужно")
