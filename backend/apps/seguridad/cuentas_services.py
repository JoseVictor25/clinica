"""Creación y consulta de cuentas ligadas a identidades de la clínica."""

from django.db import transaction
from django.db.models import Q

from apps.core.api_exceptions import Conflicto, RecursoNoEncontrado
from apps.core.seed_data import ROL_PACIENTE
from apps.pacientes.models import Paciente
from apps.personal.models import Personal
from apps.personal.role_policy import (
    resolver_rol_obligatorio,
    validar_roles_para_personal,
)

from .models import Rol, Usuario, UsuarioRol
from .services import crear_usuario_clinica


def _conflicto_cuenta_verificable(tipo):
    raise Conflicto(
        f"Ya existe una cuenta verificable mediante el registro de {tipo} con la misma CI.",
        codigo="cuenta_existente_verificable",
    )


def crear_cuenta_para_personal(*, clinica, personal_id, datos, roles):
    """Crea y vincula una cuenta nueva al Personal en una sola transacción."""
    with transaction.atomic():
        personal = (
            Personal.all_objects.select_for_update()
            .filter(pk=personal_id, clinica=clinica)
            .first()
        )
        if personal is None:
            raise RecursoNoEncontrado("Personal no encontrado.")
        if personal.usuario_id is not None:
            raise Conflicto(
                "El personal ya tiene una cuenta vinculada.",
                codigo="personal_ya_vinculado",
            )
        if Paciente.all_objects.filter(
            clinica=clinica, ci=personal.ci, usuario__isnull=False
        ).exists():
            _conflicto_cuenta_verificable("paciente")

        roles = validar_roles_para_personal(roles, personal.cargo)
        if any(not rol.estado for rol in roles):
            raise Conflicto("Uno de los roles está inactivo.", codigo="rol_inactivo")

        # Se resuelve antes de crear el usuario para no dejar cuentas parciales.
        obligatorio = resolver_rol_obligatorio(
            clinica=clinica, cargo=personal.cargo, bloquear=True
        )
        roles_efectivos = list(roles)
        if obligatorio and all(rol.pk != obligatorio.pk for rol in roles_efectivos):
            roles_efectivos.append(obligatorio)

        usuario = crear_usuario_clinica(
            clinica,
            {**datos, "estado": True},
            roles=roles_efectivos,
        )
        personal.usuario = usuario
        personal.save(update_fields=["usuario"])
        Paciente.all_objects.filter(
            clinica=clinica, ci=personal.ci
        ).update(email=usuario.email)
        return personal


def crear_cuenta_para_paciente(*, clinica, paciente_id, datos):
    """Crea una cuenta Paciente y la vincula atómicamente."""
    with transaction.atomic():
        paciente = (
            Paciente.all_objects.select_for_update()
            .filter(pk=paciente_id, clinica=clinica)
            .first()
        )
        if paciente is None:
            raise RecursoNoEncontrado("Paciente no encontrado.")
        if not paciente.estado:
            raise Conflicto("El paciente está inactivo.", codigo="paciente_inactivo")
        if paciente.usuario_id is not None:
            raise Conflicto(
                "El paciente ya tiene una cuenta vinculada.",
                codigo="paciente_ya_vinculado",
            )
        if Personal.all_objects.filter(
            clinica=clinica, ci=paciente.ci, usuario__isnull=False
        ).exists():
            _conflicto_cuenta_verificable("personal")

        rol = Rol.all_objects.filter(
            clinica=clinica, nombre=ROL_PACIENTE, estado=True
        ).first()
        if rol is None:
            raise Conflicto(
                "El rol Paciente no está disponible.", codigo="rol_paciente_no_disponible"
            )
        usuario = crear_usuario_clinica(
            clinica,
            {**datos, "estado": True},
            roles=[rol],
            permitir_rol_paciente=True,
        )
        paciente.usuario = usuario
        paciente.email = usuario.email
        paciente.save(update_fields=["usuario", "email"])
        return paciente


def cuentas_elegibles_para_personal(*, clinica, personal, search=""):
    queryset = Usuario.all_objects.filter(
        clinica=clinica,
        personal__isnull=True,
        paciente__clinica=clinica,
        paciente__ci=personal.ci,
    )
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )
    return queryset.prefetch_related("roles_asignados__rol").order_by("username")


def cuentas_elegibles_para_paciente(*, clinica, paciente, search=""):
    queryset = Usuario.all_objects.filter(
        clinica=clinica,
        estado=True,
        paciente__isnull=True,
        personal__clinica=clinica,
        personal__ci=paciente.ci,
    )
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )
    return queryset.prefetch_related("roles_asignados__rol").order_by("username")


def asegurar_rol_paciente(usuario, clinica):
    rol = Rol.all_objects.filter(
        clinica=clinica, nombre=ROL_PACIENTE, estado=True
    ).first()
    if rol is None:
        raise Conflicto(
            "El rol Paciente no está disponible.", codigo="rol_paciente_no_disponible"
        )
    UsuarioRol.all_objects.get_or_create(usuario=usuario, rol=rol)
