from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
]
