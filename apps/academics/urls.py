from django.urls import path

from . import views

urlpatterns = [
    path("schedule/", views.schedule, name="schedule"),
    path("teachers/", views.teachers, name="teachers"),
    path("free-rooms/", views.free_rooms, name="free_rooms"),
    path("grades/", views.grades, name="grades"),
    path("subject/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("exams/", views.exams, name="exams"),
    path("deadlines/", views.deadlines, name="deadlines"),
    path("exams/<int:pk>/retake-deadline/", views.add_retake_deadline, name="exam_retake_deadline"),
    path("schedule/<int:pk>/homework-deadline/", views.add_homework_deadline, name="homework_deadline"),
]
