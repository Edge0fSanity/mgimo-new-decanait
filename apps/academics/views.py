import math
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import StudentProfile

from .models import Deadline, Exam, Grade, ScheduleEntry, Subject, percent_to_mark

# Соц. блок (0,1) нигде не вводится — считаем зачтённым (100%).
SOCIAL_PERCENT = 100

# Цели калькулятора: (процент рейтинга, подпись).
RATING_GOALS = [(60, "не получить задолженность"), (75, "хорошо"), (90, "отлично")]


def _avg(values):
    return sum(values) / len(values) if values else None


def _base_percent(subject, current_avg):
    """Накопленный процент без сессии: текущий контроль + соц. блок."""
    return float(subject.weight_current) * current_avg + float(subject.weight_social or 0) * SOCIAL_PERCENT


def _rating(subject, current_avg, exam_percent):
    """Итоговый процент по формуле положения: (процент, финальный) или None.

    None — схема оценивания не задана или текущий контроль ещё не накоплен.
    """
    if subject.weight_current is None or subject.weight_exam is None or current_avg is None:
        return None
    base = _base_percent(subject, current_avg)
    if exam_percent is None:
        return base, False
    return base + float(subject.weight_exam) * exam_percent, True


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
        prev_week = next_week = None
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
        prev_week = (week_of - timedelta(days=7)).isoformat()
        next_week = (week_of + timedelta(days=7)).isoformat()
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
            "prev_week": prev_week if view == "week" else None,
            "next_week": next_week if view == "week" else None,
            "profile": profile,
        },
    )


@login_required
def grades(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    # Несколько строк на дисциплину (аттестация + сессия): для карточки берём последнюю.
    by_subject = {}
    # prefetch_related и словарь экзаменов — против N+1 (T28): 2 запроса вместо 2N.
    for g in profile.grades.select_related("subject").prefetch_related("subject__control_elements"):
        kept = by_subject.get(g.subject_id)
        if kept is None or g.updated_at > kept.updated_at:
            by_subject[g.subject_id] = g
    exams_by_subject = {}
    for exam in profile.exams.order_by("scheduled_at"):
        exams_by_subject.setdefault(exam.subject_id, exam)
    cards, ratings, debts = [], [], 0
    for grade in by_subject.values():
        subject = grade.subject
        elements = list(subject.control_elements.all())
        entered = [float(e.percent) for e in elements if e.percent is not None]
        current_avg = _avg(entered)
        exam_percent = float(grade.percent) if grade.percent is not None else None
        rating = _rating(subject, current_avg, exam_percent)
        if rating:
            ratings.append(rating[0])
        if grade.status == Grade.Status.DEBT:
            debts += 1
        cards.append(
            {
                "grade": grade,
                "subject": subject,
                "exam": exams_by_subject.get(subject.pk),
                "elements": elements,
                "current_avg": round(current_avg) if current_avg is not None else None,
                "missing_count": len(elements) - len(entered),
                "rating": round(rating[0]) if rating else None,
                "rating_final": rating[1] if rating else False,
                "rating_mark": percent_to_mark(rating[0]) if rating else None,
            }
        )
    summary = None
    if ratings:
        avg = sum(ratings) / len(ratings)
        summary = {
            "percent": round(avg),
            "mark": percent_to_mark(avg),
            "subjects": len(by_subject),
            "debts": debts,
        }
    return render(
        request,
        "academics/grades.html",
        {"cards": cards, "summary": summary, "profile": profile},
    )


@login_required
def subject_detail(request, pk):
    """Калькулятор рейтинга дисциплины: расчёт только по request.user, чужая дисциплина — 404."""
    profile = get_object_or_404(StudentProfile, user=request.user)
    subject = get_object_or_404(
        Subject.objects.filter(Q(grade__student=profile) | Q(exam__student=profile)), pk=pk
    )
    grade = profile.grades.filter(subject=subject).order_by("-updated_at").first()
    exam = profile.exams.filter(subject=subject).order_by("scheduled_at").first()
    elements = list(subject.control_elements.all())
    entered = [float(e.percent) for e in elements if e.percent is not None]
    current_avg = _avg(entered)
    weights_set = False

    n = None
    if request.GET.get("n"):
        try:
            n = min(100.0, max(0.0, float(request.GET["n"])))
        except ValueError:
            pass

    targets, slider = [], None
    if subject.weight_current is not None and subject.weight_exam is not None and current_avg is not None:
        weights_set = True
        w_exam = float(subject.weight_exam)
        base = _base_percent(subject, current_avg)
        for goal, label in RATING_GOALS:
            needed = (goal - base) / w_exam
            if needed <= 0:
                text = "уже обеспечено при любом результате экзамена"
            elif needed > 100:
                text = f"недостижимо, максимум — {percent_to_mark(base + w_exam * 100)}"
            else:
                text = f"получить на экзамене не меньше {math.ceil(needed)}%"
            targets.append({"goal": goal, "label": label, "text": text})
        if n is not None:
            total = base + w_exam * n
            slider = {"n": int(n), "total": round(total), "mark": percent_to_mark(total)}
    return render(
        request,
        "academics/subject_detail.html",
        {
            "subject": subject,
            "grade": grade,
            "exam": exam,
            "elements": elements,
            "current_avg": round(current_avg) if current_avg is not None else None,
            "missing_count": len(elements) - len(entered),
            "weights_set": weights_set,
            "targets": targets,
            "slider": slider,
            "profile": profile,
        },
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


@login_required
def add_retake_deadline(request, pk):
    """T20: «Добавить в мои сроки» для пересдачи задолженности; чужой экзамен — 404."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    profile = get_object_or_404(StudentProfile, user=request.user)
    exam = get_object_or_404(Exam, pk=pk, student=profile)
    if exam.retake_at:
        Deadline.objects.get_or_create(
            student=profile,
            title=f"Пересдача: {exam.subject}",
            defaults={"due_at": exam.retake_at},
        )
    return redirect("grades")


@login_required
def add_homework_deadline(request, pk):
    """T23: «добавить в сроки» для задания с пары; чужое занятие — 404."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    profile = get_object_or_404(StudentProfile, user=request.user)
    entry = get_object_or_404(
        ScheduleEntry.objects.filter(group=profile.base_group).filter(
            Q(language_group="") | Q(language_group=profile.language_group)
        ),
        pk=pk,
        homework__gt="",
    )
    Deadline.objects.get_or_create(
        student=profile,
        # Дата занятия в заголовке: иначе второе задание по тому же предмету
        # найдёт первый дедлайн и не создастся.
        title=f"Задание: {entry.subject} ({entry.starts_at:%d.%m})",
        defaults={"due_at": entry.starts_at},
    )
    return redirect("schedule")


def exam_percent_needed(subject, current_avg, goal=75):
    """Нужный процент на экзамене до цели рейтинга (ceil) или None.

    None — веса не заданы, текущий контроль не накоплен, цель уже обеспечена
    или недостижима (в этих случаях строку калькулятора не показываем).
    """
    if subject.weight_current is None or subject.weight_exam is None or current_avg is None:
        return None
    needed = (goal - _base_percent(subject, current_avg)) / float(subject.weight_exam)
    if needed <= 0 or needed > 100:
        return None
    return math.ceil(needed)
