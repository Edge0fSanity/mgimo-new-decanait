"""Тесты T7/T9: регистрация StudentProfile в admin и clean()-валидация Announcement."""
from django.contrib import admin
from django.core.exceptions import ValidationError

from apps.accounts.models import StudentProfile
from apps.communications.models import Announcement

from .base import BaseTestCase


class AnnouncementCleanTests(BaseTestCase):
    def test_group_announcement_with_group_is_valid(self):
        announcement = Announcement(
            title="Тестовое объявление",
            body="Текст",
            audience=Announcement.Audience.GROUP,
            group=self.user_a.student_profile.base_group,
        )
        announcement.full_clean()  # не поднимает ValidationError

    def test_group_announcement_without_group_is_rejected(self):
        announcement = Announcement(
            title="Объявление без группы",
            body="Текст",
            audience=Announcement.Audience.GROUP,
        )
        with self.assertRaises(ValidationError):
            announcement.full_clean()


class StudentProfileAdminTests(BaseTestCase):
    def test_student_profile_registered_for_view_and_change(self):
        model_admin = admin.site._registry[StudentProfile]
        self.assertIn("display_name", model_admin.search_fields)
        self.assertIn("user__username", model_admin.search_fields)
        self.assertFalse(model_admin.has_add_permission(request=None))
