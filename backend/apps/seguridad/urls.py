"""Rutas de seguridad: autenticación, usuarios y roles."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CambiarPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RolViewSet,
    UsuarioRolViewSet,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("roles", RolViewSet, basename="rol")
router.register("usuario-roles", UsuarioRolViewSet, basename="usuario-rol")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "auth/cambiar-password/",
        CambiarPasswordView.as_view(),
        name="auth-cambiar-password",
    ),
    *router.urls,
]
