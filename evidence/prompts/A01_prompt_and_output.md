# A01 — prompt и фактический вывод (17.11.2026)

Prompt: задание A01 из docs/AI_TASKS.md (строки 7–13), выдан без изменений:
«Реализуй первую проверяемую вертикаль проекта “Цифровой деканат будущего”. Стек: Python 3.12, Django 5.2 LTS, Django Templates/CSS, SQLite, Argon2, серверные сессии. …» (полный текст — в docs/AI_TASKS.md).

Инструмент: Hermes Agent, модель MiniMax-M2.5-NVFP4; uv 0.13.9, Python 3.12.14, Django 5.2.19.

## Фактические команды и вывод

- `uv sync` → django==5.2.19, argon2-cffi, uv.lock зафиксирован.
- `uv run python manage.py check` → System check identified no issues (0 silenced).
- `uv run python manage.py makemigrations accounts academics requests_app` → 0001_initial ×3.
- `uv run python manage.py migrate` → Applying ... OK (все миграции).
- `uv run python manage.py test tests` → Ran 14 tests in 1.491s — OK.
- `uv run python manage.py seed_demo` (дважды) → второй запуск: без новых записей; в БД 9 занятий, 1 демо-заявка СПР-2026-0001, хеши argon2$argon2id (проверено прямым SQL-запросом к db.sqlite3).
- Smoke живого сервера `runserver 127.0.0.1:8765` + curl (две cookie-сессии):
  - GET / без сессии → 302 → /login/?next=/
  - POST /login/ demo_a → 302 → /
  - GET / → «Иванова Анна», группа МЭО-01, языковая EN-1
  - GET /schedule/?view=week → «Перенос: было 19.11 13:00 (Ауд. 112) → стало 19.11 15:00 (Ауд. 210). Перенос по болезни преподавателя (Деканат)»
  - POST /requests/new/ (справка) → 302; в SQLite появилась СПР-2026-0002 (purpose=Smoke, status=submitted)
  - POST /requests/1/ {status: ready} → 403 (CSRF-защита отклонила запрос без токена; автотест дополнительно проверяет 405 при валидном токене)
- Ошибки в процессе и исправления:
  1. Повторный seed падал IntegrityError (уникальный слот) — перенос занятия менял starts_at после создания; исправлено: перенос задан финальными значениями в плане seed.
  2. POST на /requests/<id>/ возвращал 200 — добавлен @require_http_methods(["GET"]).

## Ограничения

Деплой, HTTPS, доступ из РФ, staff-смена статуса через Admin, оценки/уведомления не выполнены (A02/A05). Пароли демо-аккаунтов сгенерированы в .secrets/demo_passwords.txt (gitignored), в коде/логах/Git их нет.
