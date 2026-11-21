from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, ThemeForm
from .models import StudentProfile

# Троттлинг подбора пароля (чек-лист A05): считаем POST-попытки входа в кэше.
# Лимиты: 5 попыток на пару IP+логин и 30 на IP за 5 минут — аудитория не блокируется,
# перебор замедляется. LocMem-кэш действует в пределах процесса воркера — для одного
# инстанса достаточно, при горизонтальном масштабировании нужен общий кэш.
LOGIN_ATTEMPTS_WINDOW = 300
LOGIN_MAX_PER_LOGIN = 5
LOGIN_MAX_PER_IP = 30


def login_throttle(view):
    """Ограничивает частоту POST-попыток входа; GET (показ формы) не считаем."""

    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        ip = request.META.get("REMOTE_ADDR", "")
        username = request.POST.get("username", "")[:150]
        per_login_key = f"login:{ip}:{username}"
        per_ip_key = f"login-ip:{ip}"
        for key, limit in ((per_login_key, LOGIN_MAX_PER_LOGIN), (per_ip_key, LOGIN_MAX_PER_IP)):
            attempts = cache.get(key, 0) + 1
            cache.set(key, attempts, LOGIN_ATTEMPTS_WINDOW)
            if attempts > limit:
                return HttpResponse(
                    "Слишком много попыток входа. Попробуйте через несколько минут.",
                    status=429,
                )
        return view(request, *args, **kwargs)

    return wrapped


@login_required
def profile(request):
    # Пользователь без профиля студента (напр. superuser) видит 404, а не 500.
    profile = get_object_or_404(StudentProfile, user=request.user)
    initials = "".join(word[0] for word in profile.display_name.split()[:2]).upper()
    if request.method == "POST":
        if "save_theme" in request.POST:
            form = ThemeForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Оформление сохранено")
        else:
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Контактные данные сохранены")
        return redirect("profile")
    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
            "initials": initials,
            "form": ProfileForm(instance=request.user),
            "theme_form": ThemeForm(instance=profile),
        },
    )
