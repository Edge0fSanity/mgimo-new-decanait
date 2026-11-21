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
        self.assertContains(page, "Сообщить о проблеме в аудитории")
        self.assertContains(page, 'name="room"')
        self.assertContains(page, "Заявок пока нет")

    def test_create_request(self):
        client = self.login(self.user_a)
        response = client.post(
            reverse("maintenance"),
            {"room": self.room.pk, "category": "computer", "description": "Не включается компьютер у окна"},
            follow=True,
        )
        self.assertRedirects(response, reverse("maintenance"))
        # Подтверждение видно студенту после редиректа.
        self.assertContains(response, "Заявка зарегистрирована")
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

    def test_nav_link_removed_and_action_on_request_list(self):
        # Пункт «Обслуживание» убран из навигации, действие доступно со страницы заявок.
        client = self.login(self.user_a)
        home = client.get(reverse("home"))
        self.assertNotContains(home, ">Обслуживание</a>")
        page = client.get(reverse("request_list"))
        self.assertContains(page, "Сообщить о проблеме в аудитории")
        self.assertContains(page, reverse("maintenance"))
