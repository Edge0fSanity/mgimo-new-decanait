"""Интеграционные тесты T18: подтипы справок, форма из 3 секций, отмена заявки."""
from django.urls import reverse

from apps.requests_app.models import RequestStatusEvent, StudentRequest

from .base import BaseTestCase

CERTIFICATE_DATA = {
    "subtype": "tax",
    "organization": "ФНС России",
    "purpose": "Для налогового вычета",
    "delivery_method": "electronic",
}


class SubtypeFormTests(BaseTestCase):
    def test_subtype_saved_and_shown_in_card_heading(self):
        client = self.login(self.user_a)
        # Форма одной страницей: шаг подтверждения показывает данные профиля.
        page = client.get(reverse("request_create"))
        self.assertContains(page, "Иванова Анна")
        self.assertContains(page, "ФМЭП")
        self.assertContains(page, "Способ получения")

        response = client.post(reverse("request_create"), CERTIFICATE_DATA)
        obj = self.user_a.requests.get()
        self.assertEqual(obj.subtype, StudentRequest.Subtype.TAX)
        self.assertEqual(obj.organization, "ФНС России")
        self.assertEqual(obj.delivery_method, StudentRequest.Delivery.ELECTRONIC)
        self.assertRedirects(response, reverse("request_detail", args=[obj.pk]))
        # Заголовок карточки: «Справка · для налогового вычета».
        self.assertContains(client.get(reverse("request_detail", args=[obj.pk])), "для налогового вычета")

    def test_form_requires_subtype_organization_purpose_delivery(self):
        client = self.login(self.user_a)
        response = client.post(reverse("request_create"), {})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field in ("subtype", "organization", "purpose", "delivery_method"):
            self.assertIn(field, form.errors, field)
        self.assertFalse(StudentRequest.objects.exists())

    def test_application_keeps_content_without_subtype(self):
        client = self.login(self.user_b)
        client.post(reverse("request_create_kind", args=["zayavlenie"]), {"content": "Прошу перевести меня"})
        obj = self.user_b.requests.get()
        self.assertEqual(obj.type, StudentRequest.Type.APPLICATION)
        self.assertEqual(obj.subtype, "")
        page = client.get(reverse("request_detail", args=[obj.pk]))
        self.assertContains(page, "<h1>Заявление</h1>")


class CancelRequestTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.request_a = StudentRequest.objects.create(
            owner=self.user_a, type=StudentRequest.Type.CERTIFICATE,
            subtype=StudentRequest.Subtype.STUDY, organization="Деканат",
        )

    def test_owner_cancels_submitted_request(self):
        client = self.login(self.user_a)
        response = client.post(reverse("request_cancel", args=[self.request_a.pk]))
        self.assertRedirects(response, reverse("request_detail", args=[self.request_a.pk]))
        obj = StudentRequest.objects.get(pk=self.request_a.pk)
        self.assertEqual(obj.status, StudentRequest.Status.CANCELLED)
        event = RequestStatusEvent.objects.get(request=obj)
        self.assertEqual(event.to_status, StudentRequest.Status.CANCELLED)
        self.assertEqual(event.actor, self.user_a)
        # Отменённая заявка больше не предлагает отмену.
        self.assertNotContains(client.get(reverse("request_detail", args=[obj.pk])), "Отменить заявку")

    def test_cancel_other_users_request_is_404(self):
        client = self.login(self.user_b)
        self.assertEqual(client.post(reverse("request_cancel", args=[self.request_a.pk])).status_code, 404)
        self.assertEqual(StudentRequest.objects.get(pk=self.request_a.pk).status, StudentRequest.Status.SUBMITTED)

    def test_cancel_in_progress_request_is_refused(self):
        self.request_a.status = StudentRequest.Status.IN_PROGRESS
        self.request_a.save(update_fields=["status"])
        client = self.login(self.user_a)
        self.assertEqual(client.post(reverse("request_cancel", args=[self.request_a.pk])).status_code, 404)
        self.assertEqual(StudentRequest.objects.get(pk=self.request_a.pk).status, StudentRequest.Status.IN_PROGRESS)
        self.assertEqual(RequestStatusEvent.objects.filter(request=self.request_a).count(), 0)

    def test_cancel_requires_post(self):
        client = self.login(self.user_a)
        self.assertEqual(client.get(reverse("request_cancel", args=[self.request_a.pk])).status_code, 405)
        self.assertEqual(StudentRequest.objects.get(pk=self.request_a.pk).status, StudentRequest.Status.SUBMITTED)
