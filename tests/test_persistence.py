import os
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from apps.academics.models import ScheduleEntry
from apps.requests_app.models import StudentRequest

from .base import TEST_PASSWORD, BaseTestCase


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PersistenceTests(BaseTestCase):
    def test_request_survives_relogin_and_restart(self):
        client = self.login(self.user_a)
        response = client.post(reverse("request_create"), {"type": "certificate", "purpose": "Деканат"})
        obj = self.user_a.requests.get()

        # Симуляция перезапуска процесса: закрываем соединение, читаем БД заново.
        connection.close()
        fresh = StudentRequest.objects.get(pk=obj.pk)
        self.assertEqual(fresh.purpose, "Деканат")

        # Logout / повторный вход — заявка на месте.
        client.logout()
        self.assertTrue(client.login(username=self.user_a.username, password=TEST_PASSWORD))
        response = client.get(reverse("request_detail", args=[obj.pk]))
        self.assertContains(response, obj.public_number)
        self.assertContains(response, "Подана")

    def test_seed_is_idempotent_and_keeps_user_requests(self):
        client = self.login(self.user_a)
        client.post(reverse("request_create"), {"type": "certificate", "purpose": "Моя заявка"})
        user_request = self.user_a.requests.get()

        env = {"DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD, "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD, "DEMO_STAFF_PASSWORD": TEST_PASSWORD}
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
            schedule_count = ScheduleEntry.objects.count()
            call_command("seed_demo", verbosity=0)

        self.assertEqual(ScheduleEntry.objects.count(), schedule_count)
        # Пользовательская заявка не удалена; демо-заявка создана только demo_a.
        self.assertEqual(self.user_a.requests.count(), 1)
        self.assertTrue(StudentRequest.objects.filter(pk=user_request.pk, purpose="Моя заявка").exists())
        # Повторный seed не сбрасывает пароли и не создаёт дубликаты аккаунтов.
        self.assertEqual(get_user_model().objects.filter(username__in=["demo_a", "demo_b"]).count(), 2)
        self.assertTrue(client.login(username="demo_a", password=TEST_PASSWORD))

    def test_seed_gives_different_schedules(self):
        env = {"DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD, "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD, "DEMO_STAFF_PASSWORD": TEST_PASSWORD}
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
        a = get_user_model().objects.get(username="demo_a")
        b = get_user_model().objects.get(username="demo_b")
        client_a = self.client
        self.assertTrue(client_a.login(username="demo_a", password=TEST_PASSWORD))
        page_a = client_a.get("/schedule/?view=week")
        self.assertContains(page_a, "Кузнецова Ольга")   # EN-1
        self.assertNotContains(page_a, "Орлова Мария")   # EN-2
        self.assertTrue(client_a.login(username="demo_b", password=TEST_PASSWORD))
        page_b = client_a.get("/schedule/?view=week")
        self.assertContains(page_b, "Орлова Мария")
        self.assertNotContains(page_b, "Кузнецова Ольга")
