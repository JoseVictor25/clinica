"""Reglas transaccionales de vinculación entre paciente y cuenta."""

from django.db import transaction

from apps.core.api_exceptions import Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.personal.models import Personal
from apps.seguridad.cuentas_services import asegurar_rol_paciente
from apps.seguridad.models import Usuario

from .models import Paciente


def vincular_usuario_paciente(*, clinica, paciente_id, usuario_id):
    """Vincula de forma idempotente manteniendo el orden paciente → usuario."""

    with transaction.atomic():
        paciente = (
            Paciente.objects.select_for_update()
            .filter(pk=paciente_id, clinica=clinica)
            .first()
        )
        if paciente is None:
            raise RecursoNoEncontrado("Paciente no encontrado.")

        usuario = (
            Usuario.tenant_objects.select_for_update()
            .filter(pk=usuario_id, clinica=clinica)
            .first()
        )
        if usuario is None:
            raise RecursoNoEncontrado("Usuario no encontrado.")

        if not paciente.estado:
            raise Conflicto("El paciente está inactivo.", codigo="paciente_inactivo")

        if not usuario.estado:
            raise DatosInvalidos(
                "El usuario debe estar activo.",
                codigo="usuario_no_valido",
            )

        if paciente.usuario_id is not None:
            if paciente.usuario_id == usuario.pk:
                return paciente
            raise Conflicto(
                "El paciente ya está vinculado a otra cuenta.",
                codigo="paciente_ya_vinculado",
            )

        if Paciente.all_objects.filter(usuario=usuario).exclude(pk=paciente.pk).exists():
            raise Conflicto(
                "El usuario ya está vinculado a otro paciente.",
                codigo="usuario_ya_vinculado",
            )

        identidad = Personal.all_objects.filter(
            clinica=clinica,
            ci=paciente.ci,
            usuario=usuario,
        ).exists()
        if not identidad:
            raise Conflicto(
                "La cuenta debe estar vinculada a personal con la misma CI.",
                codigo="identidad_no_coincide",
            )

        asegurar_rol_paciente(usuario, clinica)
        paciente.usuario = usuario
        paciente.email = usuario.email
        paciente.save(update_fields=["usuario", "email"])
        return paciente
