from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.accounts.models import StudentProfile

from .models import Deadline, Exam, Grade, ScheduleEntry

DAY_TITLES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _student_entries(profile, start, end):
    """Занятия основной группы плюс занятия языковой группы студента."""
    return (
        ScheduleEntry.objects.filter(
            group=profile.base_group,
            starts_at__gte=start,
            starts_at__lt=end,
        )
        .filter(Q(language_group="") | Q(language_group=profile.language_group))
        .select_related("subject")
        .order_by("starts_at")
    )


@login_required
def schedule(request):
    """Расписание на сегодня или неделю, при необходимости заданную через week_of."""
    view = request.GET.get("view", "today")
    moscow = ZoneInfo("Europe/Moscow")
    today = timezone.localdate(timezone=moscow)
    if view == "week":
        week_of = today
        try:
            requested_date = date.fromisoformat(request.GET.get("week_of", ""))
        except ValueError:
            pass
        else:
            if 1 < requested_date.year < 9999:
                week_of = requested_date
        start = datetime.combine(week_of - timedelta(days=week_of.weekday()), time.min, moscow)
        day_count = 7
        title = "Расписание недели"
    else:
        view = "today"
        start = datetime.combine(today, time.min, moscow)
        day_count = 1
        title = "Сегодня"
    end = start + timedelta(days=day_count)

    profile = get_object_or_404(StudentProfile, user=request.user)
    entries = list(_student_entries(profile, start, end))
    days = []
    for offset in range(day_count):
        day = (start + timedelta(days=offset)).date()
        day_entries = [e for e in entries if timezone.localdate(e.starts_at, moscow) == day]
        days.append(
            {
                "date": day,
                "title": DAY_TITLES[day.weekday()],
                "entries": day_entries,
                "is_today": day == today,
            }
        )
    return render(
        request,
        "academics/schedule.html",
        {
            "view": view,
            "title": title,
            "days": days,
            "shows_today": start.date() <= today < end.date(),
            "profile": profile,
        },
    )


@login_required
def grades(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    return render(
        request,
        "academics/grades.html",
        {"grades": profile.grades.select_related("subject"), "profile": profile},
    )


@login_required
def exams(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    return render(
        request,
        "academics/exams.html",
        {"exams": profile.exams.select_related("subject"), "profile": profile},
    )


@login_required
def deadlines(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    items = Deadline.objects.filter(Q(group=profile.base_group) | Q(student=profile)).filter(
        due_at__gte=timezone.now()
    )
    return render(request, "academics/deadlines.html", {"deadlines": items, "profile": profile})
