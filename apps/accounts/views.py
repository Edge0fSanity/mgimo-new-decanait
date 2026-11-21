import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AvatarForm, ProfileForm, ThemeForm
from .models import StudentProfile


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
        elif "save_avatar" in request.POST:
            # T40: фото профиля. Старый файл забираем до биндинга формы: после валидации
            # profile.photo — уже новый загруженный файл, delete() затёр бы его.
            old_photo = profile.photo if profile.photo else None
            form = AvatarForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                if old_photo:
                    old_photo.delete(save=False)
                form.save()
                messages.success(request, "Фото профиля обновлено")
            else:
                # `or {}` — идиома проекта (forms.py:13): Pyright считает errors Optional.
                for errors in (form.errors or {}).values():
                    for error in errors:
                        messages.error(request, error)
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
            "avatar_form": AvatarForm(instance=profile),
        },
    )


@login_required
@require_http_methods(["GET"])
def avatar(request, pk):
    # T40: личный файл раздаётся только владельцу; чужой аватар не существует (404).
    profile = get_object_or_404(StudentProfile, pk=pk, user=request.user)
    if not profile.photo:
        raise Http404("Фото не загружено")
    content_type = mimetypes.guess_type(profile.photo.name)[0] or "application/octet-stream"
    return FileResponse(profile.photo.open("rb"), content_type=content_type)


@login_required
def my_group(request):
    # Список своей группы; идентификатора группы в URL нет — чужой состав показать нельзя.
    profile = get_object_or_404(StudentProfile, user=request.user)
    classmates = StudentProfile.objects.filter(base_group=profile.base_group).order_by("display_name")
    return render(request, "accounts/my_group.html", {"profile": profile, "classmates": classmates})
