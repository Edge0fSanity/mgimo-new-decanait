from django.contrib import admin
from django.db import transaction

from apps.communications.models import Notification

from .models import DemoDocument, RequestStatusEvent, StudentRequest


def _transition(queryset, to_status, note, actor):
    """Смена статуса атомарно создаёт событие истории и уведомление студенту."""
    for obj in queryset:
        with transaction.atomic():
            old = obj.status
            if old == to_status:
                continue
            obj.status = to_status
            obj.save(update_fields=["status", "updated_at"])
            RequestStatusEvent.objects.create(
                request=obj, from_status=old, to_status=to_status, actor=actor, note=note
            )
            Notification.objects.create(
                recipient=obj.owner,
                kind="status",
                title=f"Заявка {obj.public_number}: {obj.get_status_display()}",
                target_url=f"/requests/{obj.pk}/",
            )


def mark_ready(modeladmin, request, queryset):
    _transition(queryset, StudentRequest.Status.READY, "Документ готов к выдаче", request.user)


def mark_rejected(modeladmin, request, queryset):
    _transition(queryset, StudentRequest.Status.REJECTED, "Заявка отклонена", request.user)


mark_ready.short_description = "Отметить «Готово»"
mark_rejected.short_description = "Отклонить"


@admin.register(StudentRequest)
class StudentRequestAdmin(admin.ModelAdmin):
    list_display = ("public_number", "type", "owner", "status", "submitted_at")
    list_filter = ("status", "type")
    actions = [mark_ready, mark_rejected]


@admin.register(DemoDocument)
class DemoDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "request", "created_at")


# Оценки и экзамены в admin не регистрируются: служебная роль не работает с ними (ARCHITECTURE §5).
