import os
import tempfile
import unittest.mock as mock
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from .base import TEST_PASSWORD, BaseTestCase


class NoProfileTests(BaseTestCase):
    """Пользователь без StudentProfile (напр. superuser) получает 404, а не 500."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.staff = get_user_model().objects.create_user("admin_user", password=TEST_PASSWORD)

    def test_home_and_profile_404_without_profile(self):
        self.assertTrue(self.client.login(username="admin_user", password=TEST_PASSWORD))
        self.assertEqual(self.client.get("/").status_code, 404)
        self.assertEqual(self.client.get(reverse("profile")).status_code, 404)


class SeedPasswordFallbackTests(BaseTestCase):
    """Без env-паролей seed генерирует случайные и пишет их в .secrets (gitignored)."""

    def test_generated_passwords_work_and_are_written_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: "" for k in ("DEMO_STUDENT_A_PASSWORD", "DEMO_STUDENT_B_PASSWORD")}
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch("apps.accounts.management.commands.seed_demo.BASE_DIR", Path(tmp)):
                    call_command("seed_demo", verbosity=0)
                    path = os.path.join(tmp, ".secrets", "demo_passwords.txt")
                    with open(path, encoding="utf-8") as f:
                        lines = dict(l.strip().split("=", 1) for l in f if "=" in l)
            self.assertEqual(set(lines), {"demo_a", "demo_b", "demo_staff"})
            self.assertTrue(self.client.login(username="demo_a", password=lines["demo_a"]))
            self.assertTrue(self.client.login(username="demo_b", password=lines["demo_b"]))
