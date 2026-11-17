from django.urls import reverse

from apps.requests_app.models import StudentRequest

from .base import BaseTestCase


def create_request(client, **overrides):
    data = {"type": "certificate", "purpose": "Военный учебный центр", "content": ""}
    data.update(overrides)
    return client.post(reverse("request_create"), data)


class IsolationTests(BaseTestCase):
    """A→B и B→A: чужая заявка не существует (404), подмена владельца/статуса игнорируется."""

    def test_b_gets_404_on_a_request(self):
        client = self.login(self.user_a)
        response = create_request(client)
        request_a = self.user_a.requests.get()
        client_b = self.login(self.user_b)
        response = client_b.get(reverse("request_detail", args=[request_a.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(client_b.get(reverse("request_list")), request_a.public_number)

    def test_a_gets_404_on_b_request(self):
        client_b = self.login(self.user_b)
        create_request(client_b, type="application", purpose="", content="Прошу перевести меня")
        request_b = self.user_b.requests.get()
        client_a = self.login(self.user_a)
        self.assertEqual(client_a.get(reverse("request_detail", args=[request_b.pk])).status_code, 404)
        self.assertNotContains(client_a.get(reverse("request_list")), request_b.public_number)

    def test_owner_and_status_spoofing_ignored(self):
        client_b = self.login(self.user_b)
        create_request(client_b, owner=self.user_a.pk, status=StudentRequest.Status.READY)
        obj = self.user_b.requests.get()
        self.assertEqual(obj.owner, self.user_b)
        self.assertEqual(obj.status, StudentRequest.Status.SUBMITTED)

    def test_student_cannot_change_status_via_post(self):
        client = self.login(self.user_a)
        create_request(client)
        obj = self.user_a.requests.get()
        response = client.post(reverse("request_detail", args=[obj.pk]), {"status": "ready"})
        self.assertEqual(response.status_code, 405)
        obj.refresh_from_db()
        self.assertEqual(obj.status, StudentRequest.Status.SUBMITTED)

    def test_profiles_are_isolated(self):
        client_b = self.login(self.user_b)
        response = client_b.get(reverse("profile"))
        self.assertContains(response, "Петров Борис")
        self.assertNotContains(response, "Иванова Анна")
