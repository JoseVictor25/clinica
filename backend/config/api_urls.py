"""Rutas versionadas de la API del Sprint 1."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.seguridad.urls")),
    path("", include("apps.clinicas.urls")),
    path("", include("apps.personal.urls")),
]
