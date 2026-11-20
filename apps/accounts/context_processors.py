"""Контекст T19.4: предыдущий вход студента (из сессии, ставится при login)."""
from django.utils.dateparse import parse_datetime


def last_seen(request):
    raw = request.session.get("last_seen")
    return {"last_seen": parse_datetime(raw) if raw else None}
