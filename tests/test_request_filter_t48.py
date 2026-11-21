"""Тесты ревью п.13 (T48): фильтр списка заявок по типу/подтипу."""
from django.urls import reverse

from apps.requests_app.models import StudentRequest

from .base import BaseTestCase


class RequestFilterTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        StudentRequest.objects.create(
            owner=cls.user_a, type=StudentRequest.Type.CERTIFICATE, subtype=StudentRequest.Subtype.TAX
        )
        StudentRequest.objects.create(
            owner=cls.user_a, type=StudentRequest.Type.APPLICATION
        )

    def test_filter_by_type(self):
        client = self.login(self.user_a)
        page = client.get(reverse("request_list"), {"type": "certificate"})
        self.assertContains(page, "для налогового вычета")
        self.assertNotContains(page, "Заявление</strong>")
        self.assertContains(page, 'class="active" aria-current="page"')

    def test_filter_by_subtype(self):
        client = self.login(self.user_a)
        page = client.get(reverse("request_list"), {"type": "certificate", "subtype": "tax"})
        self.assertContains(page, "для налогового вычета")

    def test_unknown_values_ignored(self):
        client = self.login(self.user_a)
        page = client.get(reverse("request_list"), {"type": "hack", "subtype": "x"})
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Заявление</strong>")

    def test_filter_empty_state(self):
        client = self.login(self.user_a)
        page = client.get(reverse("request_list"), {"type": "certificate", "subtype": "visa"})
        self.assertContains(page, "Заявок по выбранному фильтру нет")

    def test_pagination_keeps_filter(self):
        for i in range(21):
            StudentRequest.objects.create(
                owner=self.user_a, type=StudentRequest.Type.CERTIFICATE, subtype=StudentRequest.Subtype.TAX
            )
        client = self.login(self.user_a)
        page = client.get(reverse("request_list"), {"type": "certificate", "page": 2})
        self.assertContains(page, "?type=certificate&amp;page=1")
