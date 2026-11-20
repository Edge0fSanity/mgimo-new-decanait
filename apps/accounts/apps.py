from django.apps import AppConfig
from django.contrib.auth import user_logged_in
from django.utils import timezone


def update_last_seen(sender, request, user, **kwargs):
    """T19.4: прежний last_seen — в сессию (для метки «новое»), текущее время — в профиль."""
    profile = getattr(user, "student_profile", None)  # нет профиля (staff) — метки не нужны
    if profile is None:
        return
    request.session["last_seen"] = profile.last_seen.isoformat() if profile.last_seen else None
    profile.last_seen = timezone.now()
    profile.save(update_fields=["last_seen"])


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        user_logged_in.connect(update_last_seen)
