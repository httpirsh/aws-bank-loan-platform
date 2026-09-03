"""
URL configuration for loans_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("office/", include("office.urls"))
]

# This section is required to integrate vite processing.
# Refer to https://medium.com/@lohit-behera/integrating-django-with-vite-react-a346f829045d

assets_url_pattern = '|'.join([
    settings.ASSETS_URL.lstrip('/')
])

urlpatterns += [
    re_path(
        rf'^(?!({assets_url_pattern})).*$',
        ensure_csrf_cookie(TemplateView.as_view(template_name='index.html')),
    ),
]

urlpatterns += static(settings.ASSETS_URL, document_root=settings.ASSETS_ROOT)