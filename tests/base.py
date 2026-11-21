"""Общие фикстуры для интеграционных тестов A01."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import StudentProfile
from apps.academics.models import Group

# Пароль только для автотестов; демо-пароли в код не попадают (см. seed_demo).
TEST_PASSWORD = "Test-Password-2026!"


def make_student(username, name, lang, spec):
    group, _ = Group.objects.get_or_create(code="1МЭО-01-01", defaults={"title": "Тестовая группа"})
    user = get_user_model().objects.create_user(username, password=TEST_PASSWORD, first_name=name.split()[0], last_name=name.split()[1])
    StudentProfile.objects.create(
        user=user, display_name=name, faculty="МЭО",
        program="Международные экономические отношения", year=1,
        base_group=group, language_group=lang, specialization=spec,
    )
    return user


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = make_student("student_a", "Иванова Анна", "EN-1", "Мировая экономика")
        cls.user_b = make_student("student_b", "Петров Борис", "EN-2", "Международные финансы")

    def login(self, user):
        # force_login: axes требует request в authenticate(), client.login() его не передаёт.
        client = self.client
        client.force_login(user)
        return client
