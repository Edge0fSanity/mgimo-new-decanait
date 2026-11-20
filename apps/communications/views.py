from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import StudentProfile

from .models import Announcement, Notification


@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user)
    return render(
        request,
        "communications/notifications.html",
        {"notifications": items, "has_unread": items.filter(read_at__isnull=True).exists()},
    )


@login_required
@require_http_methods(["POST"])
def notification_read_all(request):
    # Владелец проверяется фильтром: чужие уведомления не затрагиваются.
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return redirect("notifications")


@login_required
@require_http_methods(["POST"])
def notification_read(request, pk):
    # Чужое уведомление не существует для этого пользователя: 404 без содержимого.
    obj = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if obj.read_at is None:
        obj.read_at = timezone.now()
        obj.save(update_fields=["read_at"])
    return redirect("notifications")


@login_required
def announcements(request):
    """Архив объявлений (T4): тот же фильтр аудитории, что на главной."""
    profile = get_object_or_404(StudentProfile, user=request.user)
    items = (
        Announcement.objects.filter(
            Q(audience=Announcement.Audience.ALL) | Q(group=profile.base_group)
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .order_by("-published_at")
    )
    return render(request, "communications/announcements.html", {"announcements": items})
