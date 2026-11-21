FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Сначала только манифесты: слой зависимостей не пересобирается при правке кода.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra prod

COPY . .

RUN useradd -m app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media
USER app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# Живость: страница входа отвечает (200/302); бизнес-таблицы не затрагивает.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/login/', timeout=5)"

# Миграции и collectstatic при старте; gunicorn с числом воркеров из env (старт с 3).
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3}"]
