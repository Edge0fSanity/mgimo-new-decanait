"""Тесты T8/T12: read-only inline истории статусов и поиск/select_related в admin заявок."""
from django.contrib import admin
from django.test import TestCase

from apps.requests_app.admin import StudentRequestAdmin
from apps.requests_app.models import RequestStatusEvent, StudentRequest


class StudentRequestAdminConfigTests(TestCase):
    def test_status_history_is_readonly_inline(self):
        # T8: история статусов видна сотруднику в карточке заявки, но не редактируема.
        model_admin = admin.site._registry[StudentRequest]
        self.assertIsInstance(model_admin, StudentRequestAdmin)
        inlines = [i for i in model_admin.inlines if i.model is RequestStatusEvent]
        self.assertEqual(len(inlines), 1)
        inline = inlines[0]
        self.assertEqual(inline.extra, 0)
        self.assertFalse(inline.can_delete)
        self.assertEqual(
            set(inline.readonly_fields),
            {"from_status", "to_status", "actor", "note", "created_at"},
        )
        self.assertFalse(inline(RequestStatusEvent, admin.site).has_add_permission(None, obj=None))

    def test_search_and_select_related_configured(self):
        # T12: поиск по номеру/логину/ФИО и один запрос списка с owner.
        model_admin = admin.site._registry[StudentRequest]
        self.assertEqual(
            model_admin.search_fields,
            ("public_number", "owner__username", "owner__student_profile__display_name"),
        )
        self.assertEqual(model_admin.list_select_related, ("owner",))
