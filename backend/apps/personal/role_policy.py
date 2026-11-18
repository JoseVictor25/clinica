"""Política central de roles asociados al cargo de Personal."""

from apps.core.api_exceptions import Conflicto, DatosInvalidos
from apps.core.seed_data import (
    ROL_CONDUCTOR,
    ROL_ENFERMERIA,
    ROL_MEDICO,
    ROL_PACIENTE,
    ROL_RECEPCIONISTA,
)
from apps.seguridad.models import Rol, UsuarioRol

from .models import CargoPersonal, Personal


ROL_POR_CARGO = {
    CargoPersonal.MEDICO: ROL_MEDICO,
    CargoPersonal.ENFERMERIA: ROL_ENFERMERIA,
    CargoPersonal.RECEPCION: ROL_RECEPCIONISTA,
    CargoPersonal.CONDUCTOR: ROL_CONDUCTOR,
}

def nombre_rol_obligatorio(cargo):
    return ROL_POR_CARGO.get(cargo)


def validar_roles_para_personal(roles, cargo):
    """Valida roles pedidos por el formulario de una cuenta laboral."""
    roles = list(roles)
    if any(rol.nombre == ROL_PACIENTE for rol in roles):
        raise DatosInvalidos(
            "El rol Paciente solo se asigna desde el registro de Pacientes.",
            codigo="rol_paciente_no_permitido",
        )
    requerido = nombre_rol_obligatorio(cargo)
    no_permitidos = sorted({
        rol.nombre for rol in roles if rol.nombre != requerido
    })
    if no_permitidos:
        raise DatosInvalidos(
            "Desde Personal solo se puede asignar el rol correspondiente al cargo.",
            codigo="rol_no_corresponde_cargo",
            detalles={"roles": no_permitidos},
        )
    return roles


def resolver_rol_obligatorio(*, clinica, cargo, bloquear=False):
    nombre = nombre_rol_obligatorio(cargo)
    if nombre is None:
        return None
    queryset = Rol.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    rol = queryset.filter(clinica=clinica, nombre=nombre).first()
    if rol is None or not rol.estado:
        raise Conflicto(
            f"El rol obligatorio {nombre} no está disponible para este cargo.",
            codigo="rol_obligatorio_no_disponible",
        )
    return rol


def garantizar_rol_obligatorio(*, clinica, cargo, usuario, bloquear=False):
    rol = resolver_rol_obligatorio(
        clinica=clinica, cargo=cargo, bloquear=bloquear
    )
    if rol is None:
        return None
    UsuarioRol.all_objects.get_or_create(usuario=usuario, rol=rol)
    return rol


def retirar_rol_del_cargo(*, clinica, cargo, usuario):
    """Retira únicamente el rol laboral derivado del cargo indicado."""
    nombre = nombre_rol_obligatorio(cargo)
    if nombre is None:
        return False
    eliminados, _ = UsuarioRol.all_objects.filter(
        usuario=usuario,
        rol__clinica=clinica,
        rol__nombre=nombre,
    ).delete()
    return eliminados > 0


def personal_activo_que_requiere(usuario, rol, bloquear=False):
    queryset = Personal.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    personal = queryset.filter(
        usuario=usuario,
        clinica_id=rol.clinica_id,
    ).first()
    if personal is None or not personal.estado:
        return None
    if nombre_rol_obligatorio(personal.cargo) != rol.nombre:
        return None
    return personal

