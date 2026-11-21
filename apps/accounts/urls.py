from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from axes.decorators import axes_dispatch

from . import views

urlpatterns = [
    path(
        "login/",
        axes_dispatch(auth_views.LoginView.as_view(template_name="registration/login.html")),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change.html",
            success_url=reverse_lazy("profile"),
        ),
        name="password_change",
    ),
]
