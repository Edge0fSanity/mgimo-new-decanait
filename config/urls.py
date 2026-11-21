"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from axes.decorators import axes_dispatch

admin.site.site_title = "Цифровой деканат — служебный интерфейс"
admin.site.site_header = "Цифровой деканат — служебный интерфейс"

urlpatterns = [
    # django-axes на обе формы входа (чек-лист A05): /admin/login/ отдельно от include.
    path("admin/login/", axes_dispatch(admin.site.login)),
    path('admin/', admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.academics.urls")),
    path("", include("apps.requests_app.urls")),
    path("", include("apps.communications.urls")),
]
