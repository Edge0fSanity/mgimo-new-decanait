"""Интеграционные тесты T25: выбор оформления в профиле и класс темы на body."""
from django.urls import reverse

from .base import BaseTestCase


class ThemeTests(BaseTestCase):
    def test_theme_saved_in_profile_and_on_body(self):
        client = self.login(self.user_a)
        # По умолчанию — Корпус МГИМО.
        self.assertContains(client.get(reverse("home")), 'class="theme-mgimo"')

        response = client.post(
            reverse("profile"), {"theme": "dark", "save_theme": "1"}
        )
        self.assertRedirects(response, reverse("profile"))
        self.user_a.student_profile.refresh_from_db()
        self.assertEqual(self.user_a.student_profile.theme, "dark")
        self.assertContains(client.get(reverse("home")), 'class="theme-dark"')
        # Выбор отображается в профиле выбранным.
        page = client.get(reverse("profile"))
        self.assertContains(page, '<option value="dark" selected>')

    def test_invalid_theme_rejected(self):
        client = self.login(self.user_a)
        client.post(reverse("profile"), {"theme": "neon", "save_theme": "1"})
        self.user_a.student_profile.refresh_from_db()
        self.assertEqual(self.user_a.student_profile.theme, "mgimo")

    def test_theme_is_per_profile(self):
        # Смена темы A не затрагивает профиль B.
        client = self.login(self.user_a)
        client.post(reverse("profile"), {"theme": "neutral", "save_theme": "1"})
        self.user_b.student_profile.refresh_from_db()
        self.assertEqual(self.user_b.student_profile.theme, "mgimo")
        self.assertContains(
            self.login(self.user_b).get(reverse("home")), 'class="theme-mgimo"'
        )
