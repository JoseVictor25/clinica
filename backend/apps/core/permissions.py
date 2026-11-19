"""Permisos base y permisos por rol del Sprint 1."""

from rest_framework.permissions import BasePermission

from apps.core.seed_data import (
    ROL_ADMIN_CLINICA,
    ROL_MEDICO,
    ROL_PACIENTE,
    ROL_RECEPCIONISTA,
)


def _usuario_autenticado(usuario):
    return bool(usuario and usuario.is_authenticated)


def tiene_rol(usuario, nombre_rol):
    if not _usuario_autenticado(usuario) or not getattr(usuario, "clinica_id", None):
        return False

    from apps.seguridad.models import UsuarioRol

    return UsuarioRol.all_objects.filter(
        usuario=usuario,
        rol__nombre=nombre_rol,
        rol__estado=True,
    ).exists()


class TieneClinica(BasePermission):
    """Permite el acceso solo a usuarios autenticados con clínica."""

    message = "El usuario no está asociado a una clínica."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            _usuario_autenticado(usuario)
            and getattr(usuario, "clinica_id", None)
        )


class EsAdminSistema(BasePermission):
    """Permite el acceso solo al administrador de plataforma (sin clínica)."""

    message = "Solo el administrador del sistema puede realizar esta acción."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            _usuario_autenticado(usuario)
            and getattr(usuario, "is_superuser", False)
            and not getattr(usuario, "clinica_id", None)
        )


class EsAdminClinica(BasePermission):
    """Permite el acceso al rol Administrador de clínica."""

    message = "Se requiere el rol Administrador de clínica."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_ADMIN_CLINICA)


class EsMedico(BasePermission):
    """Permite el acceso al rol Médico."""

    message = "Se requiere el rol Médico."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_MEDICO)


class EsPaciente(BasePermission):
    """Permite el acceso al portal al rol Paciente habilitado."""

    message = "Se requiere el rol Paciente."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_PACIENTE)


class EsMedicoOPaciente(BasePermission):
    """Permite el acceso al rol Médico o Paciente."""

    message = "Se requiere el rol Médico o Paciente."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_MEDICO) or tiene_rol(
            request.user, ROL_PACIENTE
        )


class PuedeAccederEstudiosMedicos(BasePermission):
    """Permite acceso a estudios médicos a pacientes, médicos y admin de clínica."""

    message = "El rol del usuario no permite acceder a estudios médicos."

    def has_permission(self, request, view):
        return any(
            tiene_rol(request.user, rol)
            for rol in (ROL_PACIENTE, ROL_MEDICO, ROL_ADMIN_CLINICA)
        )


class EsAdminClinicaOMedico(BasePermission):
    """Permite el acceso al administrador de clínica o a un médico."""

    message = "Se requiere el rol Administrador de clínica o Médico."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_ADMIN_CLINICA) or tiene_rol(
            request.user, ROL_MEDICO
        )


class PuedeConsultarEnfermedades(EsAdminClinicaOMedico):
    """Lectura clínica para administradores de clínica y médicos."""

    message = "El rol del usuario no permite consultar enfermedades."


class PuedeConsultarAlergias(EsAdminClinicaOMedico):
    """Lectura de alergias para administradores de clínica y médicos."""

    message = "El rol del usuario no permite consultar alergias."


class EsAdminClinicaORecepcionista(BasePermission):
    message = "Se requiere el rol Administrador de clínica o Recepcionista."

    def has_permission(self, request, view):
        return tiene_rol(request.user, ROL_ADMIN_CLINICA) or tiene_rol(request.user, ROL_RECEPCIONISTA)


class PuedeConsultarPacientes(BasePermission):
    message = "El rol del usuario no permite consultar pacientes."

    def has_permission(self, request, view):
        return any(tiene_rol(request.user, rol) for rol in (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA, ROL_MEDICO))


class PuedeConsultarRecursosCita(BasePermission):
    """Lectura de especialidades y médicos necesaria para crear citas."""

    message = "El rol del usuario no permite consultar recursos de citas."

    def has_permission(self, request, view):
        return any(
            tiene_rol(request.user, rol)
            for rol in (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA, ROL_MEDICO)
        )


class EsAdminSistemaOAdminClinica(BasePermission):
    """Permite al administrador de plataforma o al de la clínica."""

    message = "Se requiere ser administrador del sistema o de la clínica."

    def has_permission(self, request, view):
        usuario = request.user
        if not _usuario_autenticado(usuario):
            return False
        if (
            getattr(usuario, "is_superuser", False)
            and not getattr(usuario, "clinica_id", None)
        ):
            return True
        return tiene_rol(usuario, ROL_ADMIN_CLINICA)


class TieneSuscripcionVigente(BasePermission):
    """Exige una suscripción vigente para los endpoints de negocio."""

    message = "La clínica no tiene una suscripción vigente."

    def has_permission(self, request, view):
        usuario = request.user
        if not _usuario_autenticado(usuario):
            return False

        # El administrador del sistema no pertenece a ninguna clínica.
        if getattr(usuario, "is_superuser", False) and not getattr(
            usuario, "clinica_id", None
        ):
            return True

        if not getattr(usuario, "clinica_id", None):
            return False

        if not hasattr(request, "_suscripcion_vigente_cache"):
            from apps.clinicas.services import suscripcion_vigente

            request._suscripcion_vigente_cache = suscripcion_vigente(
                usuario.clinica
            )

        if request._suscripcion_vigente_cache is None:
            from apps.core.api_exceptions import SuscripcionVencida

            raise SuscripcionVencida()

        return True
