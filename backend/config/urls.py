"""Rutas del proyecto. Admin, salud, documentación y API v1."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health, raiz

urlpatterns = [
    path("", raiz, name="raiz"),
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
