from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Notification


@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user)
    return render(request, "communications/notifications.html", {"notifications": items})


@login_required
@require_http_methods(["POST"])
def notification_read(request, pk):
    # Чужое уведомление не существует для этого пользователя: 404 без содержимого.
    obj = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if obj.read_at is None:
        obj.read_at = timezone.now()
        obj.save(update_fields=["read_at"])
    return redirect("notifications")
