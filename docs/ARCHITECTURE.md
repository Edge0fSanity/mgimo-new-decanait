08 ARCHITECTURE — Деканат · стек, границы и модель данных  
Решение на старт разработки · 17.11.2026 · статус: принято как базовая архитектура; реальное приложение ещё не создано в основном репозитории.

1\. Цель и приоритет  
К 22.11.2026 23:59 МСК создать публичное HTTPS-приложение, доступное из РФ без VPN и работающее минимум до итогов 28.11. Два изолированных вымышленных студента, личное расписание, оценки/сессия, заявки/справки со статусами, документы-образцы, объявления/уведомления, главный экран, мобильность от 360 px. Функции P1 только после прохождения P0.  
Источники: PRD, QA, отчёт Product Owner. Настоящие системы и аккаунты МГИМО не используются.

2\. Решение о стеке  
Один Django-монолит без отдельного SPA и API-сервера:  
— Python 3.12, Django 5.2 LTS (поддерживаемая ветка); конкретные версии зависимостей зафиксировать в lock-файле при установке.  
— Django Templates \+ CSS \+ минимальный vanilla JavaScript (без внешних JS/CDN на критическом пути); единый адаптивный интерфейс.  
— Встроенные django.contrib.auth, sessions, admin, messages, ORM, миграции и CSRF.  
— Argon2 через django.contrib.auth.hashers.Argon2PasswordHasher как приоритетный hasher; проверить фактический алгоритм в базе.  
— SQLite на постоянном серверном томе для небольшой демонстрации; миграции, backup/restore, один writer, не сбрасывать БД при redeploy. Если хостинг не гарантирует постоянный том — перейти на PostgreSQL до публикации.  
— Gunicorn \+ Caddy (TLS) \+ Docker Compose на VPS, кандидат — сервер с проверенным доступом из РФ. Провайдер, тариф, домен и бюджет не выбраны и не оплачены.  
— pytest-django для интеграционных тестов; минимум 1 независимый браузерный прогон каждого P0-сценария.  
Не использовать FastAPI-код из прежнего независимого эксперимента без отдельного решения; это другой стек. Не выдавать эксперимент за выполненный этап нового Django-проекта.

3\. Рекомендуемые Django apps и ответственность  
accounts — User (штатная модель auth), StudentProfile, вход/выход, тестовые аккаунты.  
academics — Group, Subject, ScheduleEntry, Grade, Exam, Deadline.  
requests\_app — StudentRequest, RequestStatusEvent, DemoDocument.  
communications — Announcement, Notification.  
dashboard — композиция ближайшей пары, сроков, оценок, заявок.  
config — settings, urls, middleware, раздельные env-настройки.  
Технические имена агент может немного скорректировать в первом коммите, но после миграции контракт фиксируется в репозитории.

4\. Минимальный контракт данных  
StudentProfile: user OneToOne, display\_name, faculty, program, year, base\_group FK, language\_group (строка или FK), specialization (опционально), created\_at/updated\_at.  
Group: code, title. Subject: title, short\_title.  
ScheduleEntry: group FK, optional language\_group, optional specialization, subject FK, starts\_at/ends\_at, room, teacher (полностью фиктивное имя), old\_starts\_at/old\_room, change\_reason, change\_source\_role, changed\_at. По умолчанию показать общегрупповые и только подходящие конкретному студенту занятия; нельзя выбирать чужой student\_id из браузера.  
Grade: student FK, subject FK, grade\_label/value (может отсутствовать), status enum recorded/not\_entered/credit/debt, source\_label, updated\_at. Exam: student FK, subject FK, scheduled\_at, result/status. Никакого выдуманного официального алгоритма рейтинга.  
Deadline: group FK либо student FK, title, due\_at.  
StudentRequest: owner FK User, public\_number unique, type enum enrollment\_certificate/application, payload с разрешёнными полями, status enum submitted/in\_progress/ready/rejected, submitted\_at, updated\_at; reason обязательна при rejected. Никаких полей owner\_id в принимаемом от студента payload.  
RequestStatusEvent: request FK, from\_status, to\_status, actor FK User, note, created\_at; хранит историю, статус не меняется студентом.  
DemoDocument: owner FK User, request FK optional, generated content/template, created\_at; только HTML/PDF-образец с явной надписью «Образец, недействителен».  
Announcement: title, body, audience (all/group), published\_at, expires\_at. Notification: student FK User, kind, title, target\_url/ссылка на допустимый свой объект, read\_at, created\_at.  
Выбранные поля могут уточняться разработчиком до первой миграции. Не добавлять произвольные JSON-поля, если достаточно явных колонок.

5\. Серверный контроль доступа  
— Для всех студентских ресурсов исходная личность — request.user; каждый queryset ограничен владельцем. URL /requests/\<id\>/ возвращает 404, если запись чужая; аналогично оценки, документы, уведомления.  
— На POST/PUT нельзя менять owner, status, read\_at другого пользователя через подставленные значения.  
— Вход с неверным паролем даёт одинаковую ошибку для несуществующего логина и неверного пароля; rate limiting попыток входа и журнал без паролей.  
— Cookies HttpOnly, Secure при HTTPS, SameSite; штатная защита CSRF для всех изменяющих POST, корректные ALLOWED\_HOSTS/CSRF\_TRUSTED\_ORIGINS, DEBUG=False.  
— Admin: отдельная служебная учётная запись is\_staff без superuser; назначить только permissions для заявок, статусов, объявлений/переносов. Не регистрировать оценки в видимом admin для этой роли, либо закрыть право view. Каждое изменение статуса атомарно создаёт событие и уведомление.  
— Никогда не класть пароли, секреты, реальные персональные данные, сырые ответы опроса и приватные ключи в Git/Docs/скриншоты. Демо-пароли передаются жюри только через разрешённый закрытый канал подачи.  
— Не доверять скрытым кнопкам как защите; тестировать прямые URL и POST запросы из сессий A и B.

6\. Минимальные маршруты  
/login, /logout, /, /profile, /schedule?view=today\|week, /grades, /exams, /requests, /requests/new, /requests/\<id\>, /documents/\<id\>, /notifications, /notifications/\<id\>/read, /admin/.  
Использовать Django views и формы, API JSON необязателен. URL и имена маршрутов зафиксировать в тестах. Публичные файлы static не должны содержать персональные данные. Скачивание личного документа только через проверенный Django view, не по прямому /media/ URL.

7\. Тестовый набор и готовность  
Seed двух вымышленных студентов одной основной группы, разных языковых групп и специализаций; у A и B разные расписания, оценки, дедлайны, заявки. Seed идемпотентен и не удаляет изменения.  
Минимальный тест: A вошёл → видит свой профиль и пары → подал заявку → обновил страницу и перезашёл → заявка сохранилась в SQLite → B не видит заявку A и получает 404 по URL и при прямом запросе → студент не может выставить ready; staff меняет статус с записью истории и уведомлением.  
Фактические результаты фиксировать в QA только после запуска, без приписок PASS заранее.

8\. Вне MVP  
Открытая регистрация, подключение систем вуза, загрузка вложений, чат/AI-чат, офлайн-кеш, push/email, карта корпуса, сложные графики. Калькулятор «до 4/5» и полная подпись источников — P1 после ядра.