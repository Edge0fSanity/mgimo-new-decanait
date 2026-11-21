"""T28/T30: число SQL-запросов grades не растёт с числом дисциплин; пагинация списков."""
from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurrentControlElement, Exam, Grade, Subject
from apps.requests_app.models import StudentRequest

from .base import BaseTestCase


class GradesQueryCountTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.profile = cls.user_a.student_profile

    def _add_subjects(self, n, offset=0):
        soon = timezone.now() + timedelta(days=30)
        for i in range(offset, offset + n):
            subject = Subject.objects.create(
                title=f"Дисциплина {i}", weight_current="0.4", weight_exam="0.5", weight_social="0.1"
            )
            Grade.objects.create(student=self.profile, subject=subject, percent="80")
            Exam.objects.create(student=self.profile, subject=subject, scheduled_at=soon)
            CurrentControlElement.objects.create(subject=subject, title="Контрольная", percent="70")

    def _queries(self, client):
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(client.get(reverse("grades")).status_code, 200)
        return len(ctx)

    def test_grades_queries_do_not_grow_with_subjects(self):
        client = self.login(self.user_a)
        self._add_subjects(1)
        before = self._queries(client)
        self._add_subjects(5, offset=1)
        self.assertEqual(self._queries(client), before)


class PaginationTests(BaseTestCase):
    def test_request_list_paginates(self):
        for i in range(21):
            StudentRequest.objects.create(
                owner=self.user_a, type=StudentRequest.Type.CERTIFICATE, purpose=f"причина {i}"
            )
        client = self.login(self.user_a)
        page1 = client.get(reverse("request_list"))
        self.assertEqual(page1.status_code, 200)
        self.assertContains(page1, "?page=2")
        page2 = client.get(reverse("request_list"), {"page": 2})
        self.assertContains(page2, "?page=1")
        # 20 на странице: на второй остаётся одна заявка.
        self.assertEqual(page2.content.decode().count("request-card"), 1)
