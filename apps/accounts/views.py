from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm
from .models import StudentProfile


@login_required
def profile(request):
    # Пользователь без профиля студента (напр. superuser) видит 404, а не 500.
    profile = get_object_or_404(StudentProfile, user=request.user)
    initials = "".join(word[0] for word in profile.display_name.split()[:2]).upper()
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Контактные данные сохранены")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(
        request, "accounts/profile.html", {"profile": profile, "initials": initials, "form": form}
    )
