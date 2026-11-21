"""Тесты T48: заявки на обслуживание кабинетов (дефекты аудиторий)."""
from django.urls import reverse

from apps.academics.models import Room
from apps.requests_app.models import MaintenanceRequest

from .base import BaseTestCase


class MaintenanceTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.room, _ = Room.objects.get_or_create(name="Ауд. 301")

    def test_page_shows_form_and_empty_list(self):
        client = self.login(self.user_a)
        page = client.get(reverse("maintenance"))
        self.assertContains(page, "Обслуживание кабинетов")
        self.assertContains(page, 'name="room"')
        self.assertContains(page, "Заявок пока нет")

    def test_create_request(self):
        client = self.login(self.user_a)
        response = client.post(
            reverse("maintenance"),
            {"room": self.room.pk, "category": "computer", "description": "Не включается компьютер у окна"},
        )
        self.assertRedirects(response, reverse("maintenance"))
        obj = MaintenanceRequest.objects.get(owner=self.user_a)
        self.assertEqual(obj.room, self.room)
        self.assertEqual(obj.status, MaintenanceRequest.Status.SUBMITTED)
        # Созданная заявка видна в списке со статусом.
        page = client.get(reverse("maintenance"))
        self.assertContains(page, "Ауд. 301")
        self.assertContains(page, "Принята")

    def test_rejects_unknown_category(self):
        client = self.login(self.user_a)
        client.post(
            reverse("maintenance"),
            {"room": self.room.pk, "category": "ufo", "description": "..."},
        )
        self.assertFalse(MaintenanceRequest.objects.filter(owner=self.user_a).exists())

    def test_list_shows_only_own_requests(self):
        # IDOR: чужие заявки не видны.
        MaintenanceRequest.objects.create(
            owner=self.user_b, room=self.room, category="heating", description="Батарея холодная"
        )
        client = self.login(self.user_a)
        page = client.get(reverse("maintenance"))
        self.assertNotContains(page, "Батарея холодная")
        self.assertContains(page, "Заявок пока нет")

    def test_nav_link_present(self):
        client = self.login(self.user_a)
        page = client.get(reverse("home"))
        self.assertContains(page, reverse("maintenance"))
