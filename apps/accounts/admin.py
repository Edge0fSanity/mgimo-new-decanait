from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # Создание студентов остаётся за superuser: staff получает только просмотр/правку.
    list_display = ("display_name", "user", "base_group", "year")
    search_fields = ("display_name", "user__username")

    def has_add_permission(self, request):
        return False
