from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read-all/", views.notification_read_all, name="notification_read_all"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
    path("announcements/", views.announcements, name="announcements"),
]
