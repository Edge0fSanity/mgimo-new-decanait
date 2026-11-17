"""Идемпотентный seed двух вымышленных студентов.

Пароли не хранятся в коде: берутся из env DEMO_STUDENT_A_PASSWORD /
DEMO_STUDENT_B_PASSWORD; если не заданы — генерируются случайно и один раз
записываются в gitignored файл .secrets/demo_passwords.txt (в stdout печатается
только путь, не сам пароль). Повторный запуск не удаляет и не сбрасывает заявки.
"""
import secrets
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.academics.models import Group, ScheduleEntry, Subject
from apps.requests_app.models import RequestStatusEvent, StudentRequest

BASE_DIR = Path(__file__).resolve().parents[4]


def _password(env_name: str, label: str) -> str:
    import os

    value = os.environ.get(env_name)
    if value:
        return value
    generated = secrets.token_urlsafe(12)
    secrets_dir = BASE_DIR / ".secrets"
    secrets_dir.mkdir(exist_ok=True)
    path = secrets_dir / "demo_passwords.txt"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{label}={generated}\n")
    return generated


class Command(BaseCommand):
    help = "Создать/обновить демо-данных двух студентов (идемпотентно)"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        group, _ = Group.objects.get_or_create(
            code="МЭО-01", defaults={"title": "Международные экономические отношения, 1 курс"}
        )
        subjects = {}
        for title in ["Микроэкономика", "Иностранный язык", "История международных отношений", "Математический анализ"]:
            subjects[title], _ = Subject.objects.get_or_create(title=title)

        specs = [
            ("demo_a", "Иванова Анна", "ФМЭП", "Международные экономические отношения", 1, "EN-1", "Мировая экономика"),
            ("demo_b", "Петров Борис", "ФМЭП", "Международные экономические отношения", 1, "EN-2", "Международные финансы"),
        ]
        users = {}
        for username, name, faculty, program, year, lang, spec in specs:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(_password(f"DEMO_STUDENT_{username[-1].upper()}_PASSWORD", username))
                user.first_name = name.split()[0]
                user.last_name = name.split()[1]
                user.save()
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "display_name": name,
                    "faculty": faculty,
                    "program": program,
                    "year": year,
                    "base_group": group,
                    "language_group": lang,
                    "specialization": spec,
                },
            )
            users[username] = user
        self.stdout.write("Аккаунты и профили готовы")

        # Расписание текущей недели (Пн..Пт): общие пары + пары языковых групп.
        now = timezone.localtime()
        monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        plan = [  # (день, час, предмет, lang, аудитория, преподаватель)
            (0, 10, "Микроэкономика", "", "Ауд. 301", "проф. Смирнов Пётр"),
            (0, 13, "Иностранный язык", "EN-1", "Ауд. 112", "Кузнецова Ольга"),
            (0, 13, "Иностранный язык", "EN-2", "Ауд. 118", "Орлова Мария"),
            (1, 10, "История международных отношений", "", "Ауд. 205", "доц. Волков Игорь"),
            (2, 12, "Математический анализ", "", "Ауд. 401", "доц. Соколова Елена"),
            (3, 10, "Микроэкономика", "", "Ауд. 301", "проф. Смирнов Пётр"),
            (3, 15, "Иностранный язык", "EN-1", "Ауд. 210", "Кузнецова Ольга"),
            (3, 13, "Иностранный язык", "EN-2", "Ауд. 118", "Орлова Мария"),
            (4, 10, "История международных отношений", "", "Ауд. 205", "доц. Волков Игорь"),
        ]
        for day, hour, subject, lang, room, teacher in plan:
            starts = monday + timedelta(days=day, hours=hour)
            entry, created = ScheduleEntry.objects.get_or_create(
                group=group,
                language_group=lang,
                subject=subjects[subject],
                starts_at=starts,
                defaults={
                    "ends_at": starts + timedelta(hours=1, minutes=30),
                    "room": room,
                    "teacher": teacher,
                },
            )
            # Демонстрационный перенос: занятие EN-1 в четверг было в 13:00, стало в 15:00.
            if created and lang == "EN-1" and day == 3:
                entry.old_starts_at = starts - timedelta(hours=2)
                entry.old_room = "Ауд. 112"
                entry.change_reason = "Перенос по болезни преподавателя"
                entry.change_source_role = "Деканат"
                entry.changed_at = timezone.now()
                entry.save()
        self.stdout.write("Расписание недели готово")

        # Одна демо-заявка у A, только если у него ещё нет ни одной.
        a = users["demo_a"]
        if not StudentRequest.objects.filter(owner=a).exists():
            req = StudentRequest.objects.create(
                owner=a,
                type=StudentRequest.Type.CERTIFICATE,
                purpose="Военный учебный центр",
                status=StudentRequest.Status.SUBMITTED,
            )
            RequestStatusEvent.objects.create(
                request=req, to_status=req.status, actor=a, note="Демо-заявка при seed"
            )
            self.stdout.write(f"Создана демо-заявка {req.public_number}")
        self.stdout.write(self.style.SUCCESS("Seed завершён (идемпотентно)"))
