from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.academics.models import Deadline, ScheduleEntry
from apps.communications.models import Announcement, Notification
from apps.requests_app.models import StudentRequest


@login_required
def home(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    now = timezone.now()
    next_entry = (
        ScheduleEntry.objects.filter(group=profile.base_group)
        .filter(Q(language_group="") | Q(language_group=profile.language_group))
        .filter(starts_at__gte=now)
        .select_related("subject")
        .order_by("starts_at")
        .first()
    )
    deadline = (
        Deadline.objects.filter(Q(group=profile.base_group) | Q(student=profile))
        .filter(due_at__gte=now)
        .order_by("due_at")
        .first()
    )
    active_request = (
        StudentRequest.objects.filter(
            owner=request.user,
            status__in=(StudentRequest.Status.SUBMITTED, StudentRequest.Status.IN_PROGRESS),
        )
        .order_by("-submitted_at")
        .first()
    )
    announcements = (
        Announcement.objects.filter(
            Q(audience=Announcement.Audience.ALL) | Q(group=profile.base_group)
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-published_at")[:3]
    )
    unread = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    return render(
        request,
        "dashboard/home.html",
        {
            "profile": profile,
            "next_entry": next_entry,
            "deadline": deadline,
            "active_request": active_request,
            "announcements": announcements,
            "unread": unread,
        },
    )
