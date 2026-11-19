from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.request_list, name="request_list"),
    # Две формы: /requests/new/ — справка, /requests/new/zayavlenie/ — заявление.
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/new/<str:kind>/", views.request_create, name="request_create_kind"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/sample/", views.request_sample, name="request_sample"),
    path("documents/<int:pk>/", views.document_download, name="document_download"),
]
