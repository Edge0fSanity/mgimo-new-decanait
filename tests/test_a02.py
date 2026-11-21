"""Интеграционные тесты A02: оценки/сессия, документ-образец, уведомления, дашборд, staff-действия."""
import os
import tempfile
from datetime import datetime, timezone as datetime_timezone
from unittest import mock

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Deadline, Exam, Grade, Group, ScheduleEntry, Subject
from apps.communications.models import Announcement, Notification
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

    def test_grades_in_admin_registry(self):
        # Ввод оценок/экзаменов перенесён в admin (T10): модели зарегистрированы.
        self.assertIn(Grade, admin.site._registry)
        self.assertIn(Exam, admin.site._registry)


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
        staff.user_permissions.add(Permission.objects.get(codename="change_studentrequest"))
        self.client.force_login(staff)
        url = reverse("admin:requests_app_studentrequest_changelist")
        action = {"action": "mark_rejected", "_selected_action": self.request_a.pk}

        self.assertEqual(self.client.post(url, {**action, "index": "0", "select_across": "1"}).status_code, 302)
        self.assertEqual(self.client.post(url, {
            **action, "select_across": "true", "confirm_rejection": "1", "reason": "Тест",
        }).status_code, 302)
        self.assertFalse(RequestStatusEvent.objects.filter(request=self.request_a).exists())
        self.assertContains(self.client.post(url, {**action, "index": "0"}), "Причина отклонения")
        self.client.post(url, {**action, "confirm_rejection": "1", "reason": "   "})
        self.request_a.refresh_from_db()
        self.assertEqual(self.request_a.status, StudentRequest.Status.SUBMITTED)
        action.update(confirm_rejection="1", reason="Укажите получателя справки")
        self.assertEqual(self.client.post(url, action).status_code, 302)
        obj = StudentRequest.objects.get(pk=self.request_a.pk)
        self.assertEqual(obj.status, StudentRequest.Status.REJECTED)
        event = RequestStatusEvent.objects.get(request=obj)
        self.assertEqual(event.to_status, StudentRequest.Status.REJECTED)
        self.assertEqual(event.actor, staff)
        self.assertEqual(event.note, action["reason"])
        note = Notification.objects.get(recipient=self.user_a, kind="status", title__contains=obj.public_number)
        self.assertIn(obj.public_number, note.title)
        self.assertEqual(note.target_url, f"/requests/{obj.pk}/")

        # Повторное действие того же статуса не создаёт дублей; смена на ready создаёт новое событие.
        self.client.post(url, action)
        self.assertEqual(RequestStatusEvent.objects.filter(request=obj).count(), 1)
        self.client.force_login(self.user_a)
        self.assertContains(self.client.get(reverse("request_detail", args=[obj.pk])), action["reason"])
        self.client.force_login(staff)
        self.client.post(url, {"action": "mark_ready", "index": "0", "_selected_action": obj.pk})
        self.assertEqual(StudentRequest.objects.get(pk=obj.pk).status, StudentRequest.Status.READY)
        self.assertEqual(RequestStatusEvent.objects.filter(request=obj).count(), 2)

    def test_ready_sample_requires_owner_and_ready_status(self):
        url = reverse("request_sample", args=[self.request_a.pk])
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.request_a.status = StudentRequest.Status.READY
        self.request_a.save(update_fields=["status"])
        response = self.client.get(url)
        self.assertContains(response, "Образец. Не имеет юридической силы.")
        self.assertContains(response, self.request_a.public_number)
        self.assertTrue(response.headers["Content-Disposition"].startswith("attachment;"))
        self.client.force_login(self.user_b)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)


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

    def test_home_uses_moscow_date_and_links_to_week_of_next_class(self):
        ScheduleEntry.objects.create(
            group=self.user_a.student_profile.base_group,
            subject=self.subject,
            starts_at="2026-12-28T09:30:00+03:00",
            ends_at="2026-12-28T11:00:00+03:00",
            room="Новая аудитория",
            old_room="Прежняя аудитория",
            teacher="Тестовый преподаватель",
        )
        frozen = datetime(2026, 12, 26, 21, 30, tzinfo=datetime_timezone.utc)
        with timezone.override("UTC"), mock.patch("django.utils.timezone.now", return_value=frozen):
            self.client.force_login(self.user_a)
            home = self.client.get(reverse("home"))
            self.assertContains(home, 'datetime="2026-12-27"')
            self.assertContains(home, "09:30")
            self.assertContains(home, "Прежняя аудитория")
            self.assertContains(home, "?view=week&amp;week_of=2026-12-28")
            self.assertContains(self.client.get("/schedule/?view=today"), "Занятий нет")
            week = self.client.get("/schedule/?view=week&week_of=2026-12-28")
            self.assertContains(week, "Новая аудитория")
            self.assertContains(week, "Прежняя аудитория")
            self.assertNotContains(week, 'href="#schedule-today"')


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
