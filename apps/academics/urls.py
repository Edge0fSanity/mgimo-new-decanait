from django.urls import path

from . import views

urlpatterns = [
    path("schedule/", views.schedule, name="schedule"),
    path("grades/", views.grades, name="grades"),
    path("exams/", views.exams, name="exams"),
    path("deadlines/", views.deadlines, name="deadlines"),
]
