"""Тесты T21: профиль — инициалы, учебные данные только просмотр, факультет МЭО, смена пароля."""
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from .base import TEST_PASSWORD, BaseTestCase

BASE_DIR = Path(__file__).resolve().parent.parent


class ProfileViewTests(BaseTestCase):
    def test_initials_rendered_from_display_name(self):
        client = self.login(self.user_a)
        page = client.get(reverse("profile"))
        self.assertContains(page, 'class="initials"')
        self.assertContains(page, ">ИА<")

    def test_academic_data_readonly_with_report_link(self):
        client = self.login(self.user_a)
        page = client.get(reverse("profile"))
        # Учебные данные показываются, но не редактируются: нет полей формы для них.
        self.assertContains(page, "EN-1")
        self.assertNotContains(page, 'name="language_group"')
        self.assertNotContains(page, 'name="specialization"')
        self.assertNotContains(page, 'name="base_group"')
        # «Сообщить об ошибке» ведёт на заявление.
        self.assertContains(page, reverse("request_create_kind", args=["zayavlenie"]))
        # Одна кнопка «Выйти» — в шапке base.html.
        self.assertEqual(page.content.decode().count(">Выйти<"), 2)

    def test_email_editable(self):
        client = self.login(self.user_a)
        response = client.post(reverse("profile"), {"email": "anna@example.com"})
        self.assertRedirects(response, reverse("profile"))
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.email, "anna@example.com")

    def test_group_code_components(self):
        # Ревью п.2: код «4МЭО-03-21» = 4 курс МЭО, 3 академическая группа, 21 языковая.
        from apps.academics.models import Group

        self.assertEqual(
            Group(code="4МЭО-03-21").code_description,
            "4МЭО-03-21 · 4 курс · академическая 03 · языковая 21",
        )
        self.assertEqual(Group(code="МЭО-01").code_description, "МЭО-01")
        client = self.login(self.user_a)
        self.assertContains(client.get(reverse("profile")), "академическая 01")


class PasswordChangeTests(BaseTestCase):
    def test_change_password_accessible_and_works(self):
        client = self.login(self.user_a)
        self.assertEqual(client.get(reverse("password_change")).status_code, 200)
        response = client.post(
            reverse("password_change"),
            {
                "old_password": TEST_PASSWORD,
                "new_password1": "New-Password-2027!",
                "new_password2": "New-Password-2027!",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password("New-Password-2027!"))


class NoFmepAnywhereTests(TestCase):
    def test_fmep_absent_from_templates_seed_and_fixtures(self):
        needle = "ФМ" + "ЭП"  # без литерала, чтобы тест не находил сам себя
        hits = []
        for root in ("templates", "apps", "tests", "static"):
            for path in (BASE_DIR / root).rglob("*"):
                if path.is_file() and path.suffix in {".py", ".html", ".css"}:
                    if needle in path.read_text(encoding="utf-8"):
                        hits.append(str(path))
        self.assertEqual(hits, [])
