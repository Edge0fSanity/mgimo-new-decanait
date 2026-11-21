from django.db import connection
from django.urls import reverse

from .base import TEST_PASSWORD, BaseTestCase


class AuthTests(BaseTestCase):
    def test_wrong_password_rejected(self):
        response = self.client.post(reverse("login"), {"username": self.user_a.username, "password": "wrong-password"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_unknown_user_same_error(self):
        response = self.client.post(reverse("login"), {"username": "nobody", "password": "wrong-password"})
        self.assertContains(response, "Неверный логин или пароль")

    def test_unauthenticated_redirects_to_login(self):
        for url in ["/", "/profile/", "/requests/", "/requests/new/", "/requests/1/"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/login/", response["Location"])

    def test_csrf_required_on_login_and_create(self):
        strict = self.client_class(enforce_csrf_checks=True)
        response = strict.post(reverse("login"), {"username": self.user_a.username, "password": TEST_PASSWORD})
        self.assertEqual(response.status_code, 403)
        strict.force_login(self.user_a)
        response = strict.post(reverse("request_create"), {"type": "certificate", "purpose": "X"})
        self.assertEqual(response.status_code, 403)

    def test_logout_invalidates_session(self):
        self.login(self.user_a)
        self.assertEqual(self.client.get("/profile/").status_code, 200)
        self.client.post(reverse("logout"))
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)

    def test_password_stored_as_argon2(self):
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.password.startswith("argon2$"), self.user_a.password[:12])
        # соединение закрыто и открыто заново: хеш читается из БД, не из кеша
        connection.close()
        fresh = type(self.user_a).objects.get(pk=self.user_a.pk)
        self.assertTrue(fresh.password.startswith("argon2$"))
