# A02 — ядро образования и коммуникаций · 17.11.2026

## Prompt (выдан как есть)
«Выполни задание A02 из AI_TASKS.md»

Текст задания — docs/AI_TASKS.md строка 16: «На основе действующего Django-проекта добавь
оценки/зачёты/сессию, две формы заявки (справка и заявление), статусы и историю, защищённый
документ-образец, новости, дедлайны и уведомления с сохранением read_at. Добавь ограниченный
служебный интерфейс Django Admin без прав на оценки. Действие staff "готово/отклонено" создаёт
аудит и уведомление студенту. Весь новый личный контент фильтровать по request.user; покрыть
негативными тестами IDOR и прав на каждый объект. Не нарушать A01 и не заменять данные в БД
при seed. Сделай главный экран с ближайшей парой, дедлайном и активной заявкой; фиксируй
тесты и экранные доказательства.»
Критерии: D-Q03–D-Q07 PASS с логом; сохранение после рестарта.

## Инструмент
Hermes Agent, модель MiniMax-M2.5-NVFP4; uv 0.13.9, Python 3.12.14, Django 5.2.19.

## Изменённые файлы
- apps/academics: models.py (+Grade, +Exam, +Deadline), views.py (+grades/exams/deadlines),
  urls.py (+/grades/ /exams/ /deadlines/), admin.py (только Deadline), migrations/0002
- apps/requests_app: models.py (+DemoDocument), forms.py (две формы по kind),
  views.py (+document_download, request_create по kind), urls.py (+/documents/<id>/, +/requests/new/<kind>/),
  admin.py (StudentRequest с действиями mark_ready/mark_rejected), migrations/0002
- apps/communications (новое): models.py (Announcement, Notification), views.py, urls.py,
  admin.py, migrations/0001
- apps/dashboard (новое): views.py (home), urls.py
- config/settings.py (+2 приложения, MEDIA_ROOT/MEDIA_URL), config/urls.py (+2 include)
- templates/: dashboard/home.html, academics/grades.html, academics/exams.html,
  academics/deadlines.html, communications/notifications.html, request_form/list/detail, base.html
- apps/accounts/management/commands/seed_demo.py — идемпотентное расширение
- tests/test_a02.py (новое), tests/test_isolation.py, tests/test_persistence.py, tests/test_audit_fixes.py
- .env.example (+DEMO_STAFF_PASSWORD), .gitignore (+media/), README.md, docs/PROMPT_LOG.md (D-P004)

## Команды и фактический вывод
- uv run python manage.py makemigrations academics requests_app communications → 3 миграции созданы
- uv run python manage.py migrate → Applying academics.0002 / communications.0001 / requests_app.0002 ... OK
- uv run python manage.py check → System check identified no issues
- uv run python manage.py test tests → Ran 25 tests in 3.830s OK
- uv run python manage.py seed_demo → «Оценки и экзамены готовы / Seed завершён (идемпотентно)»

## Smoke живого сервера (127.0.0.1:8765, curl, три сессии)
- аноним / → 302 /login/?next=/
- demo_a: дашборд содержит «Ближайшая пара», «Ближайший дедлайн», «Моя активная заявка», СПР-2026-0002
- demo_b: дашборд «Активных заявок нет»; /grades/ без оценок A
- документ-образец: владелец 200 (внутри «ОБРАЗЕЦ — документ недействителен»), B 404, аноним 302
- /media/documents/... → 404 (файлы только через защищённый view)
- demo_staff → /admin/: видит Заявки, Объявления, Дедлайны; /admin/academics/grade/ → 404

## Ошибки в процессе и исправления
1. Скрытое поле type получало slug («spravka») вместо значения типа → заявки не создавались
   (тесты изоляции A01 упали). Исправлено: поле необязательное, тип принудительно задаёт view из URL.
2. Тесты seed без DEMO_STAFF_PASSWORD писали случайные пароли demo_staff в реальный
   .secrets/demo_passwords.txt (11 строк). Исправлено: env добавлен во все seed-тесты, файл очищен.

## Ограничения
- D-Q03–D-Q07 формально PASS ставит независимый QA-агент (A04); здесь — автотесты и smoke.
- Браузерная проверка 360 px и скриншоты — A03; деплой/доступ из РФ — A05.
- Стоимость/токены: не измерены. Ручные действия пользователя: нет.
