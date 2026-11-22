# RELEASE_AUDIT — финальный релизный аудит

Дата: 22.11.2026 ~21:30 МСК. Аудитор: независимый агент (не автор кода).
Commit аудита: **0f5563ba549fc773a62ab06e49d952034cb6df7d** (master). Внимание: origin/master = 65c10a4 — локальный master **на 1 коммит впереди и не запушен**; на сервере /opt/decanat нет .git, задеплоенный commit не зафиксирован (NOT VERIFIED).
Production: http://45.80.71.15/ — caddy/db Up 27h, web перезапущен 20:53 МСК сегодня (restarts=0, OOM нет — ручной рестарт/деплой).
Оговорка: живые HTTP-проверки велись из-под иностранного VPN (подтверждено пользователем) — часть запросов не доходила; функциональный live-проход не засчитывается.

## Сводная таблица

| # | Проверка | Статус | Доказательства |
|---|----------|--------|----------------|
| 1 | Автотесты | **PASS** | `manage.py test` на 0f5563b: **Ran 147 tests, OK** (локальный прогон 22.11) |
| 2 | D-R01 вход/профиль, 2 студента | **PASS (код+тесты) / NOT VERIFIED (live)** | tests/test_auth.py, test_isolation.py::test_profiles_are_isolated; на проде demo_a/demo_b существуют с argon2-хешами (SSH: docker compose exec web shell). Live-вход из VPN не завершён |
| 3 | D-R02–R03 расписание/оценки | **PASS (тесты) / NOT VERIFIED (live)** | tests/test_schedule_t35.py, test_expertise_week.py, test_rating.py |
| 4 | D-R04 заявки: номер/дата/статус, студент не может поставить «готово» | **PASS** | apps/requests_app/views.py:103 (owner=request.user), POST смены статуса студентом → 405 (test_isolation.py::test_student_cannot_change_status_via_post); статус меняет только admin-действие с правом change (apps/requests_app/admin.py:33) |
| 5 | D-R05 документы, пометка «Образец, недействителен», защита владельцем | **PASS** | views.py:151,162 — get_object_or_404(owner=request.user); /media/ не раздаётся Caddy (Caddyfile: только /static и reverse_proxy) |
| 6 | D-R06/07 уведомления/главный экран | **PASS (тесты) / NOT VERIFIED (live)** | tests/test_dashboard_t22.py, test_trust_t19_t20_t23.py; notification_read фильтрует recipient=request.user (apps/communications/views.py:35) |
| 7 | D-R08 мобильность 360px | **NOT VERIFIED** | Скриншоты 360/1440 в evidence/screenshots + ревью A03; полный проход D-Q08 (1440, клавиатура) не выполнен |
| 8 | Серверная изоляция студентов (IDOR) | **PASS** | 23 фильтра owner/user=request.user по apps/*/views.py; негативные тесты A→B и B→A (tests/test_isolation.py); A04-отчёт: живой IDOR-прогон 18.11 — чужая заявка 404 |
| 9 | Права admin/staff | **PASS** | demo_staff: is_staff=True, is_superuser=False (проверено SSH на проде); права ограничены списком codename (seed_demo.py:389–416); оценки/экзамены в admin не зарегистрированы |
| 10 | CSRF | **PASS** | Live: POST /login/ без токена → **403** «Ошибка проверки CSRF» (22.11); CsrfViewMiddleware в settings.py:37; тесты с enforce_csrf_checks (A04) |
| 11 | Хеширование паролей | **PASS** | Argon2id в локальной БД и на проде (SSH: demo_a/demo_b/demo_staff → argon2); PASSWORD_HASHERS[0]=Argon2 (settings.py:107) |
| 12 | Ограничение попыток входа | **PASS** | django-axes, 5 попыток/1 час, /login/ и /admin/login/ (settings.py:48–55, config/urls.py:27); tests/test_login_throttle.py (5 тестов) |
| 13 | Секреты в Git | **PASS** | Сканирование всех 165 коммитов: демо-пароли и паттерны секретов (SECRET_KEY/postgres:///AKIA) — **не найдены**; .env/.secrets/db.sqlite3/media в .gitignore; .env.example только с CHANGE_ME |
| 14 | **HTTPS** | **FAIL** | Опубликован http://45.80.71.15/; на сервере SITE_ADDRESS=:80, SESSION_COOKIE_SECURE=False, TRUST_PROXY_SSL=False (SSH .env). PRD: «HTTPS» — не выполнено. План исправления ниже |
| 15 | Сохранность заявок / миграции / перезапуск | **PASS (код+тесты) / частично NOT VERIFIED** | tests/test_persistence.py (переживает relogin+restart, seed идемпотентен); Postgres volume pgdata; на проде 4 заявки в БД (SSH). Restore прод-бэкапа не выполнялся — см. №16 |
| 16 | **Резервное копирование** | **FAIL** | На сервере нет файлов бэкапов и нет cron-задачи (SSH: «no backup files found», «no backup cron»). Команда pg_dump описана в README.md:79, но не автоматизирована. Требование QA.md A05 «Backup/restore проверен» — не закрыто |
| 17 | Доступность после перезапуска | **PASS с оговоркой** | restart: unless-stopped у всех сервисов; web перезапускался сегодня — сайт отвечает. Дефект: Docker HEALTHCHECK вечно «unhealthy» — healthcheck ходит на 127.0.0.1:8000, Host не в ALLOWED_HOSTS → 400 (подтверждено traceback в State.Health.Log). На работу не влияет, но сигнал мониторинга ложный |
| 18 | Документация/промпты/скриншоты | **FAIL (устаревшее)** | PROMPT_LOG.md (231 строка), ADR, ARCHITECTURE, evidence/qa/A04_report.md, скриншоты — есть. Но **SUBMISSION.md §«Фактическая готовность» лжив**: «URL НЕ СОЗДАН, аккаунты НЕ СОЗДАНЫ» — URL и аккаунты существуют. README.md:34 говорит про «14 тестов» (фактически 147) |
| 19 | D-Q10 доступ из РФ без VPN | **NOT VERIFIED** | Требует реальной сети РФ уполномоченным участником (QA.md:31). Критично сделать до подачи |
| 20 | D-Q12 комплект жюри | **NOT VERIFIED** | Пароли не переданы, PDF со скриншотами не собран, подтверждения подачи нет |

## Критические исправления (только эти)

1. **HTTPS (блокер PRD).** Минимальный безопасный план:
   - Завести домен (сертификат на голый IP доверенным не будет) → A-запись на 45.80.71.15.
   - В /opt/decanat/.env: `SITE_ADDRESS=домен`, `DJANGO_ALLOWED_HOSTS=домен,45.80.71.15`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://домен`, `DJANGO_SESSION_COOKIE_SECURE=True`, `DJANGO_TRUST_PROXY_SSL=True`.
   - `docker compose up -d caddy web` — Caddy сам получит сертификат Let's Encrypt; порт 80 остаётся для HTTP-01 и редиректа на HTTPS. Данные не затрагиваются (volumes не трогаем). Откат: вернуть `SITE_ADDRESS=:80` и рестартнуть caddy. Старая IP-ссылка перестанет отвечать — в подаче указывать доменную.
   - Если домен до 23:59 не успевается — подавать как есть с фиксацией ограничения в описании; переключение сделать сразу после (хостинг живёт до 28.11).
2. **Бэкап (блокер D-Q09).** Однократно: `docker compose exec db pg_dump -U decanat decanat > /root/backups/decanat-$(date +%F).sql` + cron `0 4 * * *` с той же командой; один restore в отдельной папке проверить. 10 минут, риска для прод-сайта нет.
3. **Запушить master** (0f5563b) — жюри должно видеть код, соответствующий прод-сборке; сейчас origin отстаёт на коммит.
4. **Обновить SUBMISSION.md** («Фактическая готовность») и README (число тестов) — жюри сверяет документы с реальностью.
5. **D-Q10 из сети РФ** — назначить исполнителя, зафиксировать дату/сеть/устройство (QA.md:31).

Не критично (не блокирует подачу): HEALTHCHECK unhealthy — добавить `127.0.0.1` в DJANGO_ALLOWED_HOSTS на сервере при следующем плановом деплое.

## Что проверено фактически, а что нет

Фактические прогоны: 147 автотестов (локально), скан git-истории на секреты, SSH-осмотр прод-БД (хеши, аккаунты, 4 заявки, .env), live-проверка CSRF 403, docker ps/inspect.
NOT VERIFIED: live-функциональный проход двух аккаунтов (VPN), D-Q08/D-Q10/D-Q12, restore прод-бэкапа, соответствие задеплоенного кода коммиту 0f5563b.
