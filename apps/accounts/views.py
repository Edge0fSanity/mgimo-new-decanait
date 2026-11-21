from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, ThemeForm
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


@login_required
def my_group(request):
    # Список своей группы; идентификатора группы в URL нет — чужой состав показать нельзя.
    profile = get_object_or_404(StudentProfile, user=request.user)
    classmates = StudentProfile.objects.filter(base_group=profile.base_group).order_by("display_name")
    return render(request, "accounts/my_group.html", {"profile": profile, "classmates": classmates})
