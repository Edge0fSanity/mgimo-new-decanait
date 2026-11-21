from django.core.cache import cache
from django.test import TestCase

from tests.base import BaseTestCase, TEST_PASSWORD


class LoginThrottleTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def post_login(self, username, password):
        return self.client.post("/login/", {"username": username, "password": password})

    def test_sixth_attempt_per_username_blocked(self):
        for _ in range(5):
            response = self.post_login("student_a", "wrong-password")
            self.assertEqual(response.status_code, 200)
        response = self.post_login("student_a", "wrong-password")
        self.assertEqual(response.status_code, 429)

    def test_other_username_same_ip_not_blocked(self):
        for _ in range(5):
            self.post_login("student_a", "wrong-password")
        response = self.post_login("student_b", "wrong-password")
        self.assertEqual(response.status_code, 200)

    def test_correct_password_within_limit_logs_in(self):
        response = self.post_login("student_a", TEST_PASSWORD)
        self.assertEqual(response.status_code, 302)

    def test_get_not_counted(self):
        for _ in range(10):
            self.client.get("/login/")
        response = self.post_login("student_a", TEST_PASSWORD)
        self.assertEqual(response.status_code, 302)

    def test_admin_login_throttled_too(self):
        for _ in range(5):
            self.client.post("/admin/login/", {"username": "x", "password": "y"})
        response = self.client.post("/admin/login/", {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 429)
