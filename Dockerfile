FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
# Сначала только зависимости — слой кэшируется, пока не меняется uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# Живой = /login/ отвечает 200/302 (страница с сессией, без обращения к бизнес-таблицам).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import http.client,sys; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=4); c.request('GET','/login/'); sys.exit(0 if c.getresponse().status in (200,302) else 1)"
# entrypoint: миграции + статика (T31) + gunicorn (T33); воркеры 2×CPU+1, старт с 3.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3}"]
