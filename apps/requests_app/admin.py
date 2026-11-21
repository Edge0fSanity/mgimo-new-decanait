from django import forms
from django.contrib import admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils import timezone

from apps.communications.models import Notification

from .models import DemoDocument, MaintenanceRequest, RequestStatusEvent, StudentRequest


def _transition(queryset, to_status, note, actor):
    """Смена статуса атомарно создаёт событие истории и уведомление студенту."""
    for pk in list(queryset.values_list("pk", flat=True)):
        current = StudentRequest.objects.filter(pk=pk)
        obj = current.first()
        while obj and obj.status != to_status:
            with transaction.atomic():
                updated = current.filter(status=obj.status).update(status=to_status, updated_at=timezone.now())
                if updated:
                    RequestStatusEvent.objects.create(
                        request=obj, from_status=obj.status, to_status=to_status, actor=actor, note=note
                    )
                    Notification.objects.create(
                        recipient_id=obj.owner_id,
                        kind="status",
                        title=f"Заявка {obj.public_number}: {to_status.label}",
                        target_url=f"/requests/{obj.pk}/",
                    )
                    break
            obj = current.first()


@admin.action(description="Взять в обработку", permissions=["change"])
def mark_in_progress(modeladmin, request, queryset):
    _transition(queryset, StudentRequest.Status.IN_PROGRESS, "Заявка в обработке", request.user)


@admin.action(description="Отметить готовой", permissions=["change"])
def mark_ready(modeladmin, request, queryset):
    _transition(queryset, StudentRequest.Status.READY, "Документ готов к выдаче", request.user)


class RejectionForm(forms.Form):
    reason = forms.CharField(label="Причина отклонения", max_length=200)


@admin.action(description="Отклонить", permissions=["change"])
def mark_rejected(modeladmin, request, queryset):
    select_across = modeladmin.action_form.base_fields["select_across"].clean(request.POST.get("select_across"))
    if select_across:
        modeladmin.message_user(request, "Для отклонения отметьте нужные заявки на странице.", level="warning")
        return None
    form = RejectionForm(request.POST if "confirm_rejection" in request.POST else None)
    if form.is_valid():
        _transition(queryset, StudentRequest.Status.REJECTED, form.cleaned_data["reason"], request.user)
        return None
    return TemplateResponse(request, "admin/requests_app/reject_requests.html", {
        **modeladmin.admin_site.each_context(request),
        "title": "Отклонить заявки",
        "form": form,
        "selected": request.POST.getlist(ACTION_CHECKBOX_NAME),
    })


class RequestStatusEventInline(admin.TabularInline):
    model = RequestStatusEvent
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "actor", "note", "created_at")
    verbose_name_plural = "История статусов"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StudentRequest)
class StudentRequestAdmin(admin.ModelAdmin):
    list_display = ("public_number", "type", "subtype", "owner", "status", "submitted_at")
    list_filter = ("status", "type", "subtype")
    readonly_fields = ("status",)
    actions = [mark_in_progress, mark_ready, mark_rejected]
    inlines = (RequestStatusEventInline,)
    list_select_related = ("owner",)
    search_fields = ("public_number", "owner__username", "owner__student_profile__display_name")


@admin.register(DemoDocument)
class DemoDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "request", "created_at")


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    # T48: статус дефекта кабинета ведёт staff; студент видит его на /maintenance/.
    list_display = ("room", "category", "owner", "status", "created_at")
    list_filter = ("status", "category", "room")
    list_select_related = ("owner", "room")


# Оценки и экзамены в admin не регистрируются: служебная роль не работает с ними (ARCHITECTURE §5).
