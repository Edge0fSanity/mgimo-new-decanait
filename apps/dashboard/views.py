from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.db.models import F, Min, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.academics.models import Deadline, ScheduleEntry, Subject
from apps.academics.views import exam_percent_needed
from apps.communications.models import Announcement, Notification
from apps.requests_app.models import StudentRequest

def _rating_hint(profile, now):
    """Строка калькулятора (T22) для ближайшей дисциплины студента или None."""
    candidates = (
        Subject.objects.filter(Q(grade__student=profile) | Q(exam__student=profile))
        .filter(weight_current__isnull=False, weight_exam__isnull=False)
        .annotate(
            next_at=Min(
                "scheduleentry__starts_at",
                filter=Q(scheduleentry__group=profile.base_group, scheduleentry__starts_at__gte=now),
            )
        )
        .order_by(F("next_at").asc(nulls_last=True), "pk")
        # prefetch — против N+1 по control_elements в цикле ниже (T28).
        .prefetch_related("control_elements")
    )
    for subject in candidates:
        entered = [float(e.percent) for e in subject.control_elements.all() if e.percent is not None]
        current_avg = sum(entered) / len(entered) if entered else None
        needed = exam_percent_needed(subject, current_avg)
        if needed is not None:
            return {"subject": subject, "needed": needed}
    return None


@login_required
def home(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    moscow = ZoneInfo("Europe/Moscow")
    now = timezone.localtime(timezone=moscow)
    next_entry = (
        ScheduleEntry.objects.filter(group=profile.base_group)
        .filter(Q(language_group="") | Q(language_group=profile.language_group))
        .filter(starts_at__gte=now)
        .select_related("subject")
        .order_by("starts_at")
        .first()
    )
    today = now.date()
    next_entry_date = timezone.localdate(next_entry.starts_at, moscow) if next_entry else None
    schedule_query = {"view": "today" if next_entry_date == today else "week"}
    if next_entry_date and next_entry_date != today:
        schedule_query["week_of"] = next_entry_date.isoformat()
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
    announcements = Announcement.visible_to(profile, now)[:3]
    return render(
        request,
        "dashboard/home.html",
        {
            "profile": profile,
            "today": today,
            "next_entry": next_entry,
            "schedule_url": reverse("schedule", query=schedule_query),
            "deadline": deadline,
            "rating_hint": _rating_hint(profile, now),
            "active_request": active_request,
            "announcements": announcements,
        },
    )
