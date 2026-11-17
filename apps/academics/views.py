from datetime import timedelta

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
    """Главная страница «Сегодня» и вид «Неделя»: /schedule?view=today|week."""
    view = request.GET.get("view", "today")
    now = timezone.localtime()
    if view == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        title = "Расписание недели"
    else:
        view = "today"
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        title = "Сегодня"

    profile = get_object_or_404(StudentProfile, user=request.user)
    entries = list(_student_entries(profile, start, end))
    days = []
    for offset in range((end - start).days):
        day = start + timedelta(days=offset)
        day_entries = [e for e in entries if timezone.localtime(e.starts_at).date() == day.date()]
        days.append(
            {
                "date": day.date(),
                "title": DAY_TITLES[day.weekday()],
                "entries": day_entries,
                "is_today": day.date() == now.date(),
            }
        )
    if view == "today":
        days = [d for d in days if d["is_today"]]

    return render(
        request,
        "academics/schedule.html",
        {
            "view": view,
            "title": title,
            "days": days,
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
