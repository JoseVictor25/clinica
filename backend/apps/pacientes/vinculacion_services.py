"""Reglas transaccionales de vinculación entre paciente y cuenta."""

from django.db import transaction

from apps.core.api_exceptions import Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.core.seed_data import ROL_PACIENTE
from apps.seguridad.models import Usuario, UsuarioRol

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

        rol_valido = UsuarioRol.all_objects.filter(
            usuario=usuario,
            rol__clinica=clinica,
            rol__nombre=ROL_PACIENTE,
            rol__estado=True,
        ).exists()
        if not usuario.estado or not rol_valido:
            raise DatosInvalidos(
                "El usuario debe estar activo y tener el rol Paciente habilitado.",
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

        paciente.usuario = usuario
        paciente.save(update_fields=["usuario"])
        return paciente
