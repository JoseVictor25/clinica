"""Servicios de clínicas, planes y suscripciones."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.api_exceptions import Conflicto, DatosInvalidos, LimiteUsuarios
from apps.core.seed_data import (
    ESPECIALIDADES_BASE,
    ROL_ADMIN_CLINICA,
    ROLES_BASE,
)
from apps.personal.models import Especialidad
from apps.seguridad.models import Rol, Usuario, UsuarioRol

from .models import Clinica, PlanSuscripcion, Suscripcion


def crear_roles_base(clinica):
    """Crea los roles base de una clínica de forma idempotente."""
    creados = 0
    for nombre, descripcion in ROLES_BASE:
        _, creado = Rol.all_objects.get_or_create(
            clinica=clinica,
            nombre=nombre,
            defaults={"descripcion": descripcion},
        )
        creados += int(creado)
    return creados


def crear_especialidades_base(clinica):
    """Crea las especialidades base de una clínica de forma idempotente."""
    creadas = 0
    for nombre in ESPECIALIDADES_BASE:
        _, creada = Especialidad.all_objects.get_or_create(
            clinica=clinica,
            nombre=nombre,
            defaults={"descripcion": f"Especialidad de {nombre}."},
        )
        creadas += int(creada)
    return creadas


def registrar_clinica(datos, admin_data):
    """
    Registra una clínica con sus datos base y el primer administrador.

    Todo ocurre en una sola transacción: si falla el admin o un dato único,
    no queda una clínica a medio provisionar.
    """
    if Clinica.objects.filter(nit=datos["nit"]).exists():
        raise Conflicto(
            "Ya existe una clínica con ese NIT.", codigo="nit_duplicado"
        )
    if Usuario.all_objects.filter(username=admin_data["username"]).exists():
        raise Conflicto(
            "El nombre de usuario no está disponible.",
            codigo="usuario_duplicado",
        )
    if Usuario.all_objects.filter(email=admin_data["email"]).exists():
        raise Conflicto(
            "El email no está disponible.", codigo="email_duplicado"
        )

    try:
        with transaction.atomic():
            clinica = Clinica.objects.create(**datos)
            crear_roles_base(clinica)
            crear_especialidades_base(clinica)

            rol_admin = Rol.all_objects.get(
                clinica=clinica, nombre=ROL_ADMIN_CLINICA
            )
            usuario = Usuario.all_objects.create_user(
                username=admin_data["username"],
                email=admin_data["email"],
                password=admin_data["password"],
                clinica=clinica,
                estado=True,
                is_staff=False,
            )
            UsuarioRol.all_objects.create(usuario=usuario, rol=rol_admin)
    except IntegrityError as exc:
        raise Conflicto(
            "No se pudo registrar la clínica por un conflicto de datos únicos.",
            codigo="clinica_duplicada",
        ) from exc

    return clinica


def suscripcion_vigente(clinica):
    """Devuelve la suscripción ACTIVA vigente hoy, o None."""
    hoy = timezone.localdate()
    return Suscripcion.all_objects.filter(
        clinica=clinica,
        estado=Suscripcion.Estado.ACTIVA,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy,
    ).first()


def marcar_vencidas(clinica):
    """Marca como VENCIDAS las suscripciones ACTIVA cuya fecha_fin pasó."""
    return Suscripcion.all_objects.filter(
        clinica=clinica,
        estado=Suscripcion.Estado.ACTIVA,
        fecha_fin__lt=timezone.localdate(),
    ).update(estado=Suscripcion.Estado.VENCIDA)


def _validar_fechas(fecha_inicio, fecha_fin):
    if fecha_fin < fecha_inicio:
        raise DatosInvalidos(
            "La fecha de fin no puede ser anterior a la fecha de inicio.",
            codigo="fechas_invalidas",
        )


def contar_usuarios_activos(clinica):
    return Usuario.all_objects.filter(clinica=clinica, estado=True).count()


def validar_capacidad_plan(clinica, plan):
    activos = contar_usuarios_activos(clinica)
    if activos > plan.max_usuarios:
        raise LimiteUsuarios(
            "El plan no admite la cantidad actual de usuarios activos.",
            codigo="limite_usuarios",
            detalles={
                "usuarios_activos": activos,
                "max_usuarios": plan.max_usuarios,
            },
        )


@transaction.atomic
def contratar_suscripcion(clinica, plan, fecha_inicio, fecha_fin):
    """Contrata un plan si la clínica no tiene una suscripción activa."""
    Clinica.objects.select_for_update().get(pk=clinica.pk)

    if not plan.activo:
        raise Conflicto(
            "El plan seleccionado no está activo.", codigo="plan_inactivo"
        )
    _validar_fechas(fecha_inicio, fecha_fin)
    marcar_vencidas(clinica)
    validar_capacidad_plan(clinica, plan)

    if Suscripcion.all_objects.filter(
        clinica=clinica, estado=Suscripcion.Estado.ACTIVA
    ).exists():
        raise Conflicto(
            "La clínica ya tiene una suscripción activa. Use renovar o cambiar de plan.",
            codigo="suscripcion_activa",
        )

    return Suscripcion.all_objects.create(
        clinica=clinica,
        plan=plan,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=Suscripcion.Estado.ACTIVA,
    )


@transaction.atomic
def renovar_suscripcion(suscripcion, nueva_fecha_fin):
    """Extiende la fecha de fin de una suscripción vigente."""
    suscripcion = Suscripcion.all_objects.select_for_update().get(
        pk=suscripcion.pk
    )
    if (
        suscripcion.estado != Suscripcion.Estado.ACTIVA
        or suscripcion.fecha_fin < timezone.localdate()
    ):
        raise Conflicto(
            "La suscripción no está vigente. Contrate un nuevo plan.",
            codigo="suscripcion_no_vigente",
        )
    if nueva_fecha_fin <= suscripcion.fecha_fin:
        raise DatosInvalidos(
            "La nueva fecha de fin debe ser posterior a la actual.",
            codigo="fecha_fin_invalida",
        )

    suscripcion.fecha_fin = nueva_fecha_fin
    suscripcion.save(update_fields=["fecha_fin"])
    return suscripcion


@transaction.atomic
def cambiar_plan(suscripcion, plan, fecha_inicio, fecha_fin):
    """Cancela la suscripción actual y crea una nueva con otro plan."""
    Clinica.objects.select_for_update().get(pk=suscripcion.clinica_id)
    suscripcion = Suscripcion.all_objects.select_for_update().get(
        pk=suscripcion.pk
    )

    if not plan.activo:
        raise Conflicto(
            "El plan seleccionado no está activo.", codigo="plan_inactivo"
        )
    _validar_fechas(fecha_inicio, fecha_fin)
    validar_capacidad_plan(suscripcion.clinica, plan)

    suscripcion.estado = Suscripcion.Estado.CANCELADA
    suscripcion.save(update_fields=["estado"])

    return Suscripcion.all_objects.create(
        clinica=suscripcion.clinica,
        plan=plan,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=Suscripcion.Estado.ACTIVA,
    )


@transaction.atomic
def cancelar_suscripcion(suscripcion):
    suscripcion = Suscripcion.all_objects.select_for_update().get(
        pk=suscripcion.pk
    )
    if suscripcion.estado != Suscripcion.Estado.ACTIVA:
        raise Conflicto(
            "La suscripción no está activa.", codigo="suscripcion_no_activa"
        )
    suscripcion.estado = Suscripcion.Estado.CANCELADA
    suscripcion.save(update_fields=["estado"])
    return suscripcion
