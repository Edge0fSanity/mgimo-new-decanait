"""Интеграционные тесты A02: оценки/сессия, документ-образец, уведомления, дашборд, staff-действия."""
import tempfile
from types import SimpleNamespace
from unittest import mock
import os

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from apps.academics.models import Deadline, Exam, Grade, Group, ScheduleEntry, Subject
from apps.communications.models import Announcement, Notification
from apps.requests_app.admin import mark_ready, mark_rejected
from apps.requests_app.models import DemoDocument, RequestStatusEvent, StudentRequest

from .base import TEST_PASSWORD, BaseTestCase


class A02Base(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.subject = Subject.objects.create(title="Тестовый предмет")
        cls.grade_a = Grade.objects.create(
            student=cls.user_a.student_profile, subject=cls.subject, value="5", source_label="Тест"
        )
        cls.exam_a = Exam.objects.create(
            student=cls.user_a.student_profile,
            subject=cls.subject,
            scheduled_at="2026-12-20T10:00:00+03:00",
        )
        cls.request_a = StudentRequest.objects.create(
            owner=cls.user_a, type=StudentRequest.Type.CERTIFICATE, purpose="Тестовый адресат"
        )
        cls.notification_a = Notification.objects.create(
            recipient=cls.user_a, kind="status", title="Тестовое уведомление", target_url="/"
        )


class GradesAndExamsTests(A02Base):
    def test_student_sees_only_own_grades_and_exams(self):
        client = self.login(self.user_a)
        page = client.get(reverse("grades"))
        self.assertContains(page, "Тестовый предмет")
        self.assertContains(page, "5")
        page = client.get(reverse("exams"))
        self.assertContains(page, "Тестовый предмет")

        client = self.login(self.user_b)
        self.assertContains(client.get(reverse("grades")), "Оценок пока нет")
        self.assertContains(client.get(reverse("exams")), "Экзамены не назначены")

    def test_grades_not_in_admin_registry(self):
        # Служебный интерфейс без оценок: модели не зарегистрированы ни для кого.
        self.assertNotIn(Grade, admin.site._registry)
        self.assertNotIn(Exam, admin.site._registry)


class DocumentAccessTests(A02Base):
    def test_document_download_owner_b_anon(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            doc = DemoDocument(owner=self.user_a, request=self.request_a, title="Образец")
            doc.file.save("test_doc.html", ContentFile("<h1>ОБРАЗЕЦ — документ недействителен</h1>"), save=True)

            client = self.login(self.user_a)
            response = client.get(reverse("document_download", args=[doc.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "ОБРАЗЕЦ")

            # B по прямому URL: 404 без содержимого.
            client = self.login(self.user_b)
            self.assertEqual(client.get(reverse("document_download", args=[doc.pk])).status_code, 404)

            # Без сессии: редирект на вход, без утечки.
            self.client.logout()
            response = self.client.get(reverse("document_download", args=[doc.pk]))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login/", response["Location"])

            # Прямой /media/ URL не раздаётся в urlconf.
            self.assertEqual(self.client.get("/media/documents/test_doc.html").status_code, 404)


class NotificationTests(A02Base):
    def test_read_persists_and_is_isolated(self):
        client = self.login(self.user_a)
        # GET по read-URL не меняет состояние.
        self.assertEqual(client.get(reverse("notification_read", args=[self.notification_a.pk])).status_code, 405)
        response = client.post(reverse("notification_read", args=[self.notification_a.pk]))
        self.assertRedirects(response, reverse("notifications"))
        self.assertIsNotNone(Notification.objects.get(pk=self.notification_a.pk).read_at)

        # read_at переживает «перезапуск» (закрытое соединение, чтение БД заново).
        connection.close()
        self.assertIsNotNone(Notification.objects.get(pk=self.notification_a.pk).read_at)

        # B не может отметить чужое уведомление прочитанным.
        client = self.login(self.user_b)
        self.assertEqual(client.post(reverse("notification_read", args=[self.notification_a.pk])).status_code, 404)

    def test_list_shows_only_own(self):
        client = self.login(self.user_b)
        self.assertNotContains(client.get(reverse("notifications")), "Тестовое уведомление")


class StaffActionTests(A02Base):
    def test_mark_rejected_creates_event_and_notification(self):
        staff = get_user_model().objects.create_user("staff_user", password=TEST_PASSWORD, is_staff=True)
        fake_request = SimpleNamespace(user=staff)

        mark_rejected(None, fake_request, StudentRequest.objects.filter(pk=self.request_a.pk))
        obj = StudentRequest.objects.get(pk=self.request_a.pk)
        self.assertEqual(obj.status, StudentRequest.Status.REJECTED)
        event = RequestStatusEvent.objects.get(request=obj)
        self.assertEqual(event.to_status, StudentRequest.Status.REJECTED)
        self.assertEqual(event.actor, staff)
        note = Notification.objects.get(recipient=self.user_a, kind="status", title__contains=obj.public_number)
        self.assertIn(obj.public_number, note.title)
        self.assertEqual(note.target_url, f"/requests/{obj.pk}/")

        # Повторное действие того же статуса не создаёт дублей; смена на ready создаёт новое событие.
        mark_rejected(None, fake_request, StudentRequest.objects.filter(pk=obj.pk))
        self.assertEqual(RequestStatusEvent.objects.filter(request=obj).count(), 1)
        mark_ready(None, fake_request, StudentRequest.objects.filter(pk=obj.pk))
        self.assertEqual(StudentRequest.objects.get(pk=obj.pk).status, StudentRequest.Status.READY)
        self.assertEqual(RequestStatusEvent.objects.filter(request=obj).count(), 2)


class DashboardTests(A02Base):
    def test_home_shows_pair_deadline_request(self):
        group = Group.objects.get(code="МЭО-01")
        ScheduleEntry.objects.create(
            group=group, language_group="", subject=self.subject,
            starts_at="2026-12-21T10:00:00+03:00", ends_at="2026-12-21T11:30:00+03:00",
            room="Ауд. 1", teacher="Тестовый преподаватель",
        )
        Deadline.objects.create(
            group=group, title="Тестовый дедлайн", due_at="2026-12-22T18:00:00+03:00"
        )
        client = self.login(self.user_a)
        page = client.get(reverse("home"))
        self.assertContains(page, "Тестовый предмет")
        self.assertContains(page, "Тестовый дедлайн")
        self.assertContains(page, self.request_a.public_number)

        # B не видит заявку A на главной.
        client = self.login(self.user_b)
        self.assertNotContains(client.get(reverse("home")), self.request_a.public_number)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SeedA02Tests(A02Base):
    def test_seed_creates_a02_data_idempotently(self):
        env = {
            "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
            "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
            "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
        }
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)
            counts = {m: m.objects.count() for m in (Grade, Exam, Deadline, Announcement, Notification, DemoDocument)}
            call_command("seed_demo", verbosity=0)
        for model, count in counts.items():
            self.assertEqual(model.objects.count(), count, model.__name__)

        # Демо-заявка A не задублирована и не удалена; документ-образец с пометкой.
        demo_a = get_user_model().objects.get(username="demo_a")
        self.assertEqual(demo_a.requests.count(), 1)
        doc = DemoDocument.objects.get(owner=demo_a)
        self.assertIn("недействителен", doc.file.read().decode())

        # Служебный аккаунт: staff, не superuser, с паролем из env.
        staff = get_user_model().objects.get(username="demo_staff")
        self.assertTrue(staff.is_staff)
        self.assertFalse(staff.is_superuser)
        self.assertTrue(staff.check_password(TEST_PASSWORD))
