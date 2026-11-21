"""Ревью P1-6: Moodle и библиотека — заглушки «#», скрываются до рабочих ссылок."""
import os
from unittest import mock

from django.core.management import call_command
from django.urls import reverse

from apps.dashboard.models import ExternalLink

from .base import TEST_PASSWORD, BaseTestCase


class SeedHidesStubLinksTests(BaseTestCase):
    def seed(self):
        env = {
            "DEMO_STUDENT_A_PASSWORD": TEST_PASSWORD,
            "DEMO_STUDENT_B_PASSWORD": TEST_PASSWORD,
            "DEMO_STAFF_PASSWORD": TEST_PASSWORD,
        }
        with mock.patch.dict(os.environ, env):
            call_command("seed_demo", verbosity=0)

    def test_stub_links_inactive_after_seed(self):
        self.seed()
        self.assertFalse(ExternalLink.objects.get(title="Moodle МГИМО").is_active)
        self.assertFalse(ExternalLink.objects.get(title="Библиотека МГИМО").is_active)
        self.assertTrue(ExternalLink.objects.get(title="Кафедра английского языка №2").is_active)

    def test_stub_links_not_rendered(self):
        self.seed()
        page = self.login(self.user_a).get(reverse("home"))
        self.assertNotContains(page, "Moodle МГИМО")
        self.assertNotContains(page, "Библиотека МГИМО")
        self.assertContains(page, "Кафедра английского языка №2")
