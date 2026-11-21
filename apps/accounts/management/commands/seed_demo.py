"""Идемпотентный seed двух вымышленных студентов.

Расписание создаётся на текущую и следующую неделю: идемпотентность действует
внутри недели; повторный запуск в другой неделе добавит новые занятия (старые остаются).
Пароли не хранятся в коде: берутся из env DEMO_STUDENT_A_PASSWORD /
DEMO_STUDENT_B_PASSWORD; если не заданы — генерируются случайно и один раз
записываются в gitignored файл .secrets/demo_passwords.txt (в stdout печатается
только путь, не сам пароль). Повторный запуск не удаляет и не сбрасывает заявки.
"""
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.academics.models import (
    CurrentControlElement,
    Deadline,
    Exam,
    Grade,
    Group,
    Room,
    ScheduleEntry,
    Subject,
    VacationPeriod,
)
from apps.communications.models import Announcement, Notification
from apps.dashboard.models import ExternalLink
from apps.requests_app.models import DemoDocument, MaintenanceRequest, RequestStatusEvent, StudentRequest

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
        # Код в формате МГИМО «<курс><факультет>-<академическая>-<языковая>» (ревью п.2);
        # старый демо-код «МЭО-01» переименовывается при повторном seed, но только
        # если новый код ещё не занят — иначе UNIQUE constraint роняет весь seed.
        if not Group.objects.filter(code="1МЭО-01-01").exists():
            Group.objects.filter(code="МЭО-01").update(
                code="1МЭО-01-01", title="Международные экономические отношения, 1 курс"
            )
        group, _ = Group.objects.get_or_create(
            code="1МЭО-01-01", defaults={"title": "Международные экономические отношения, 1 курс"}
        )
        subjects = {}
        for title in ["Микроэкономика", "Иностранный язык", "История международных отношений", "Математический анализ"]:
            subjects[title], _ = Subject.objects.get_or_create(title=title)

        # Веса блоков рейтинга и элементы текущего контроля (T15/T17). Веса задаём
        # только если ещё не заданы, чтобы не затирать правки из admin.
        weight_plan = {
            "Микроэкономика": ("0.40", "0.50", "0.10"),
            "Математический анализ": ("0.40", "0.50", "0.10"),
        }
        for title, weights in weight_plan.items():
            subject = subjects[title]
            if subject.weight_current is None:
                subject.weight_current, subject.weight_exam, subject.weight_social = weights
                subject.save(update_fields=["weight_current", "weight_exam", "weight_social"])
        control_plan = {  # (предмет, элемент, процент; None => «не внесено»)
            ("Микроэкономика", "Контрольная работа", "85"),
            ("Микроэкономика", "Эссэ", "78"),
            ("Математический анализ", "Коллоквиум", None),
        }
        for title, element_title, percent in control_plan:
            CurrentControlElement.objects.get_or_create(
                subject=subjects[title],
                title=element_title,
                defaults={"percent": percent},
            )

        specs = [
            ("demo_a", "Иванова Анна Сергеевна", "МЭО", "Международные экономические отношения", 1, "EN-1", "Мировая экономика"),
            ("demo_b", "Петров Борис Игоревич", "МЭО", "Международные экономические отношения", 1, "EN-2", "Международные финансы"),
        ]
        users = {}
        for username, name, faculty, program, year, lang, spec in specs:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(_password(f"DEMO_STUDENT_{username[-1].upper()}_PASSWORD", username))
                user.first_name = name.split()[1]
                user.last_name = name.split()[0]
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

        # Одногруппники для страницы «Моя группа» (ревью п.16): вход им не нужен,
        # пароль unusable — заведены, чтобы демо-группа не была из двух человек.
        for i, name in enumerate(
            ["Смирнова Мария Андреевна", "Кузьмин Дмитрий Олегович", "Орлова Елена Викторовна"], start=1
        ):
            classmate, created = User.objects.get_or_create(username=f"demo_group_{i}")
            if created:
                classmate.set_unusable_password()
                classmate.first_name = name.split()[1]
                classmate.last_name = name.split()[0]
                classmate.save()
            StudentProfile.objects.update_or_create(
                user=classmate,
                defaults={
                    "display_name": name,
                    "faculty": "МЭО",
                    "program": "Международные экономические отношения",
                    "year": 1,
                    "base_group": group,
                    "language_group": "EN-1",
                    "specialization": "Мировая экономика",
                },
            )
        self.stdout.write("Аккаунты и профили готовы")

        # Справочник аудиторий корпуса (ревью п.14): те же, что в плане расписания.
        for room in ["Ауд. 301", "Ауд. 112", "Ауд. 118", "Ауд. 205", "Ауд. 401", "Ауд. 210"]:
            Room.objects.get_or_create(name=room)

        # Каникулы (ревью п.17–18): демо-период рядом с «сегодня», чтобы баннер
        # напоминания был виден (при повторном seed поднимается, как дедлайны).
        # Зимние 25–31.01.2027 — из официального календарного графика МГИМО
        # (разбор PDF, docs/mgimo-kug-meo-2026.pdf); летние — образец, в графике
        # июнь–август занят практикой, точные даты сверить по приказу.
        today = timezone.localdate()
        VacationPeriod.objects.update_or_create(
            title="Каникулы (демо)",
            defaults={"starts_at": today + timedelta(days=5), "ends_at": today + timedelta(days=12)},
        )
        VacationPeriod.objects.get_or_create(
            title="Зимние каникулы 2026/27",
            defaults={"starts_at": date(2027, 1, 25), "ends_at": date(2027, 1, 31)},
        )
        VacationPeriod.objects.get_or_create(
            title="Летние каникулы 2027",
            defaults={"starts_at": date(2027, 6, 25), "ends_at": date(2027, 8, 31)},
        )

        # Полезные ссылки (ревью п.10, п.12): Moodle и библиотека — заглушки «#»,
        # пока реальные адреса не проверены. Из найденных страниц кафедр МЭО
        # открывается только кафедра английского языка №2 — остальные адреса
        # битые (сервер отдаёт 500), ждём корректный список.
        for i, (title, url) in enumerate(
            [
                ("Moodle МГИМО", "#"),
                ("Библиотека МГИМО", "#"),
                ("Кафедра английского языка №2", "https://mgimo.ru/study/faculty/meo/eng2/"),
            ]
        ):
            ExternalLink.objects.update_or_create(
                title=title, defaults={"url": url, "sort_order": i, "is_active": True}
            )

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
        # Две недели: в выходные текущая неделя уже в прошлом — без следующей
        # недели кабинет показывает «Предстоящих занятий нет».
        for week_offset in (0, 1):
            for day, hour, subject, lang, room, teacher in plan:
                starts = monday + timedelta(weeks=week_offset, days=day, hours=hour)
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
                if created and week_offset == 0 and lang == "EN-1" and day == 3:
                    entry.old_starts_at = starts - timedelta(hours=2)
                    entry.old_room = "Ауд. 112"
                    entry.change_reason = "Перенос по болезни преподавателя"
                    entry.change_source_role = "Деканат"
                    entry.changed_at = timezone.now()
                    entry.save()
                # Демо-задание у перенесённой пары: без него фича
                # «Добавить в дедлайны» (T23) в демо не видна.
                if week_offset == 0 and lang == "EN-1" and day == 3 and not entry.homework:
                    entry.homework = "Подготовить эссе по теме занятия"
                    entry.save(update_fields=["homework"])

        # Демо-перенос в неделю экспертизы 23–27.11.2026 (ревью P0-2): жюри,
        # открывшее эту неделю, должно увидеть и бейдж «Перенос», и кнопку
        # «Добавить в дедлайны». Перенос моделируется строкой, созданной сразу
        # с финальным starts_at и old_* полями (не правкой существующей пары).
        # Ловушка: при запуске seed рядом с этой неделей обычный цикл выше уже
        # создал пару 26.11 15:00 (week_offset=1) — тогда дозаполняем old_*.
        expertise_starts = datetime(2026, 11, 26, 15, 0)
        entry, _ = ScheduleEntry.objects.get_or_create(
            group=group,
            language_group="EN-1",
            subject=subjects["Иностранный язык"],
            starts_at=expertise_starts,
            defaults={
                "ends_at": expertise_starts + timedelta(hours=1, minutes=30),
                "room": "Ауд. 210",
                "teacher": "Кузнецова Ольга",
            },
        )
        changed = False
        if not entry.old_starts_at:
            entry.old_starts_at = expertise_starts - timedelta(hours=2)
            entry.old_room = "Ауд. 112"
            entry.change_reason = "Перенос занятия на неделю экспертизы"
            entry.change_source_role = "Деканат"
            entry.changed_at = timezone.now()
            changed = True
        if not entry.homework:
            entry.homework = "Подготовить эссе по теме занятия"
            changed = True
        if changed:
            entry.save()
        self.stdout.write("Расписание двух недель готово")

        # Одна демо-заявка у A, только если у него ещё нет ни одной.
        a = users["demo_a"]
        req = StudentRequest.objects.filter(owner=a).first()
        if not req:
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

        # Демо-заявка на обслуживание кабинета (T48), только если её ещё нет.
        demo_room = Room.objects.filter(name="Ауд. 301").first()
        if demo_room and not MaintenanceRequest.objects.filter(owner=a).exists():
            MaintenanceRequest.objects.create(
                owner=a,
                room=demo_room,
                category=MaintenanceRequest.Category.COMPUTER,
                description="Не включается компьютер у окна",
            )
            self.stdout.write("Создана демо-заявка на обслуживание Ауд. 301")

        # Оценки/зачёты/сессия: у A и B разные значения.
        profiles = {username: StudentProfile.objects.get(user=u) for username, u in users.items()}
        grade_plan = {
            "demo_a": [
                ("Микроэкономика", Grade.Status.RECORDED, "5", "Аттестация 1 модуля", "95"),
                ("Иностранный язык", Grade.Status.CREDIT, "зачёт", "Аттестация 1 модуля", None),
                ("Математический анализ", Grade.Status.DEBT, "", "Сессия 1 семестра", None),
            ],
            "demo_b": [
                ("Микроэкономика", Grade.Status.RECORDED, "4", "Аттестация 1 модуля", None),
                ("Иностранный язык", Grade.Status.CREDIT, "зачёт", "Аттестация 1 модуля", None),
                ("Математический анализ", Grade.Status.NOT_ENTERED, "", "Сессия 1 семестра", None),
            ],
        }
        for username, rows in grade_plan.items():
            for subject_title, status, value, source, percent in rows:
                Grade.objects.get_or_create(
                    student=profiles[username],
                    subject=subjects[subject_title],
                    source_label=source,
                    defaults={"status": status, "value": value, "percent": percent},
                )
        exam_at = monday + timedelta(days=7, hours=10)
        for username in ("demo_a", "demo_b"):
            Exam.objects.get_or_create(
                student=profiles[username],
                subject=subjects["Математический анализ"],
                scheduled_at=exam_at,
                defaults={"status": Exam.Status.SCHEDULED},
            )
        self.stdout.write("Оценки и экзамены готовы")

        # Дедлайны: один на группу, один персональный у A. Привязаны к «сейчас»,
        # а не к неделе seed: при запуске в конце недели привязка к понедельнику
        # даёт уже истёкшие дедлайны и пустой блок на главной. При повторном
        # seed истёкшие демо-дедлайны поднимаются (данные не стираются).
        demo_deadlines = [
            (Deadline(group=group, title="Заявление на пересдачу"), timedelta(days=4)),
            (Deadline(student=profiles["demo_a"], title="Справка в ВУЦ"), timedelta(days=3)),
        ]
        now = timezone.localtime()
        for deadline, due_in in demo_deadlines:
            existing = Deadline.objects.filter(
                group=deadline.group, student=deadline.student, title=deadline.title
            ).first()
            if existing:
                if existing.due_at < now:
                    existing.due_at = now + due_in
                    existing.save(update_fields=["due_at"])
            else:
                deadline.due_at = now + due_in
                deadline.save()

        # Объявление и уведомления (read_at остаётся пустым — студент прочитает сам).
        announcement, _ = Announcement.objects.get_or_create(
            title="Приём заявлений на пересдачу открыт",
            defaults={
                "body": "Подавайте заявление через личный кабинет до конца недели.",
                "audience": Announcement.Audience.ALL,
            },
        )
        Notification.objects.get_or_create(
            recipient=a,
            kind="status",
            target_url=f"/requests/{req.pk}/",
            defaults={"title": f"Заявка {req.public_number} принята"},
        )
        Notification.objects.get_or_create(
            recipient=users["demo_b"],
            kind="announcement",
            title=announcement.title,
            defaults={"target_url": "/"},
        )

        # Документ-образец к демо-заявке A: только через защищённый view, с пометкой «недействителен».
        if req and not DemoDocument.objects.filter(owner=a, request=req).exists():
            html = (
                "<html><body><h1>ОБРАЗЕЦ — документ недействителен</h1>"
                f"<p>Справка {req.public_number} для {profiles['demo_a'].display_name}.</p>"
                "<p>Это демонстрационный образец конкурсного концепта, юридической силы не имеет.</p></body></html>"
            )
            doc = DemoDocument(owner=a, request=req, title="Образец справки")
            doc.file.save("demo_spravka_obrazec.html", ContentFile(html), save=True)

        # Служебный аккаунт staff (не superuser): заявки, объявления; ввод основных
        # данных (справочники, расписание, оценки, дедлайны, профили) через admin.
        staff, created = User.objects.get_or_create(username="demo_staff", defaults={"is_staff": True})
        staff_pw = os.environ.get("DEMO_STAFF_PASSWORD")
        if created or staff_pw:
            # Пароль задаётся при создании и обновляется, если пароль пришёл из env.
            staff.set_password(staff_pw or _password("DEMO_STAFF_PASSWORD", "demo_staff"))
            staff.is_staff = True
            staff.save()
        staff.user_permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "view_studentrequest", "change_studentrequest",
                    "add_announcement", "change_announcement", "view_announcement",
                    "add_deadline", "change_deadline", "view_deadline",
                    "add_vacationperiod", "change_vacationperiod", "view_vacationperiod",
                    "add_externallink", "change_externallink", "view_externallink",
                    "add_group", "change_group", "view_group",
                    "add_subject", "change_subject", "view_subject",
                    "add_scheduleentry", "change_scheduleentry", "view_scheduleentry",
                    "add_grade", "change_grade", "view_grade",
                    "add_exam", "change_exam", "view_exam",
                    "add_currentcontrolelement", "change_currentcontrolelement", "view_currentcontrolelement",
                    "view_studentprofile", "change_studentprofile",
                ]
            )
        )
        self.stdout.write(self.style.SUCCESS("Seed завершён (идемпотентно)"))
