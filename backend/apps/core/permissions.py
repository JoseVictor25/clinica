"""Permisos base reutilizables. Los permisos por rol llegan en el Sprint 1."""

from rest_framework.permissions import BasePermission


class TieneClinica(BasePermission):
    """Permite el acceso solo a usuarios autenticados con clínica."""

    message = "El usuario no está asociado a una clínica."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario
            and usuario.is_authenticated
            and getattr(usuario, "clinica_id", None)
        )


class EsAdminSistema(BasePermission):
    """Permite el acceso solo al administrador de plataforma (sin clínica)."""

    message = "Solo el administrador del sistema puede realizar esta acción."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario
            and usuario.is_authenticated
            and getattr(usuario, "is_superuser", False)
            and not getattr(usuario, "clinica_id", None)
        )
