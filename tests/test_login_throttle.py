from django.test import TestCase

from tests.base import BaseTestCase, TEST_PASSWORD


class LoginAxesTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Сбрасывает записи в БД и кэш флагов блокировки (LocMem живёт между тестами).
        from axes.handlers.proxy import AxesProxyHandler

        AxesProxyHandler.reset_attempts()

    def post_login(self, username, password):
        return self.client.post("/login/", {"username": username, "password": password})

    def test_fifth_failure_locks_out(self):
        # AXES_FAILURE_LIMIT=5: блокировка срабатывает на 5-й неудачной попытке.
        for _ in range(4):
            response = self.post_login("student_a", "wrong-password")
            self.assertEqual(response.status_code, 200)
        response = self.post_login("student_a", "wrong-password")
        self.assertEqual(response.status_code, 429)

    def test_other_username_same_ip_not_locked(self):
        for _ in range(5):
            self.post_login("student_a", "wrong-password")
        response = self.post_login("student_b", "wrong-password")
        self.assertEqual(response.status_code, 200)

    def test_correct_password_after_failures_logs_in_and_resets(self):
        # Считаются только неудачные попытки: верный пароль проходит и сбрасывает счётчик.
        for _ in range(4):
            self.post_login("student_a", "wrong-password")
        response = self.post_login("student_a", TEST_PASSWORD)
        self.assertEqual(response.status_code, 302)
        for _ in range(4):
            response = self.post_login("student_a", "wrong-password")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.post_login("student_a", "wrong-password").status_code, 429)

    def test_get_not_counted(self):
        for _ in range(10):
            self.client.get("/login/")
        response = self.post_login("student_a", TEST_PASSWORD)
        self.assertEqual(response.status_code, 302)

    def test_admin_login_locked_too(self):
        for _ in range(4):
            response = self.client.post("/admin/login/", {"username": "x", "password": "y"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post("/admin/login/", {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 429)
