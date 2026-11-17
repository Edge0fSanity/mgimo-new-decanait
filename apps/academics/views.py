from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import ScheduleEntry

DAY_TITLES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _student_entries(user, start, end):
    """Занятия основной группы плюс занятия языковой группы студента."""
    profile = user.student_profile
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

    entries = list(_student_entries(request.user, start, end))
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
            "profile": request.user.student_profile,
        },
    )
