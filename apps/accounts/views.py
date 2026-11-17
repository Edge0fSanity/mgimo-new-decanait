from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import StudentProfile


@login_required
def profile(request):
    # Пользователь без профиля студента (напр. superuser) видит 404, а не 500.
    profile = get_object_or_404(StudentProfile, user=request.user)
    return render(request, "accounts/profile.html", {"profile": profile})
