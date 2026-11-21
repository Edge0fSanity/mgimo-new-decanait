from django.contrib import admin
from django.utils import timezone

from apps.academics.models import (
    CurrentControlElement,
    Deadline,
    Exam,
    Grade,
    Group,
    Room,
    ScheduleEntry,
    Subject,
    VacationPeriod,
)

admin.site.register(Group)
admin.site.register(Grade)
admin.site.register(Exam)
admin.site.register(Deadline)
admin.site.register(Room)
admin.site.register(VacationPeriod)


class CurrentControlElementInline(admin.TabularInline):
    model = CurrentControlElement
    extra = 3


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("title", "weight_current", "weight_exam", "weight_social")
    inlines = (CurrentControlElementInline,)


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ("subject", "group", "language_group", "starts_at", "room", "teacher")

    def save_model(self, request, obj, form, change):
        # Правка времени/аудитории через admin — это перенос: сохраняем прежние значения.
        if change:
            old = ScheduleEntry.objects.get(pk=obj.pk)
            if old.starts_at != obj.starts_at or old.room != obj.room:
                obj.old_starts_at = old.starts_at
                obj.old_room = old.room
                obj.changed_at = timezone.now()
            # T19.2: автор правки переноса (в тестах request может быть без user).
            obj.updated_by = getattr(request, "user", None)
        super().save_model(request, obj, form, change)
