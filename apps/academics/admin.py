from django.contrib import admin
from django.utils import timezone

from apps.academics.models import Deadline, Exam, Grade, Group, ScheduleEntry, Subject

admin.site.register(Group)
admin.site.register(Subject)
admin.site.register(Grade)
admin.site.register(Exam)
admin.site.register(Deadline)


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
        super().save_model(request, obj, form, change)
