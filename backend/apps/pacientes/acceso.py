"""Reglas de acceso de los profesionales a fichas de pacientes."""

from django.db.models import Q

from apps.atencion.models import EstadoCita
from apps.core.seed_data import ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA
from apps.core.permissions import tiene_rol


def pacientes_accesibles_para_usuario(queryset, usuario):
    """Limita a un médico a pacientes atendidos o con cita activa asignada.

    El queryset recibido debe estar limitado previamente a la clínica actual.
    Administración y recepción conservan el acceso tenant-wide.
    """
    if tiene_rol(usuario, ROL_ADMIN_CLINICA) or tiene_rol(
        usuario, ROL_RECEPCIONISTA
    ):
        return queryset

    return queryset.filter(
        Q(consultas__medico__personal__usuario=usuario)
        | Q(
            citas__medico__personal__usuario=usuario,
            citas__estado__in=(
                EstadoCita.PROGRAMADA,
                EstadoCita.CONFIRMADA,
                EstadoCita.ATENDIDA,
            ),
        )
    ).distinct()
