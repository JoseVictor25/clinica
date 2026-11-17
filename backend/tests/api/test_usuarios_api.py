"""Pruebas de usuarios, roles y asignaciones de rol."""

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connections
from rest_framework.test import APIClient

from apps.clinicas.models import PlanSuscripcion
from apps.core.seed_data import ROL_ADMIN_CLINICA, ROL_MEDICO
from apps.seguridad.models import Rol, Usuario, UsuarioRol

from .helpers import (
    CLAVE,
    cliente_autenticado,
    crear_suscripcion,
    crear_usuario_con_rol,
    token_para,
)

USUARIOS_URL = "/api/v1/usuarios/"
ROLES_URL = "/api/v1/roles/"
USUARIO_ROLES_URL = "/api/v1/usuario-roles/"


def _payload_usuario(username="nuevo", roles=None):
    datos = {
        "username": username,
        "email": f"{username}@clinica.local",
        "password": CLAVE,
    }
    if roles is not None:
        datos["roles"] = roles
    return datos


@pytest.mark.django_db
def test_admin_crea_usuario_y_asigna_roles(
    admin_a, clinica_configurada, suscripcion_amplia
):
    rol_medico = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_MEDICO
    )

    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL,
        _payload_usuario(roles=[rol_medico.pk]),
        format="json",
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "nuevo"
    assert cuerpo["roles"] == [ROL_MEDICO]
    assert "password" not in respuesta.content.decode().lower()

    creado = Usuario.all_objects.get(username="nuevo")
    assert creado.clinica_id == admin_a.clinica_id
    assert creado.is_staff is False
    assert creado.check_password(CLAVE)


@pytest.mark.django_db
def test_clinica_nunca_se_toma_del_cuerpo(
    admin_a, clinica_b, suscripcion_amplia
):
    payload = _payload_usuario()
    payload["clinica"] = clinica_b.pk

    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL, payload, format="json"
    )

    assert respuesta.status_code == 201
    creado = Usuario.all_objects.get(username="nuevo")
    assert creado.clinica_id == admin_a.clinica_id


@pytest.mark.django_db
def test_crear_usuario_sin_suscripcion_vigente(admin_a):
    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL, _payload_usuario(), format="json"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "suscripcion_vencida"
    assert not Usuario.all_objects.filter(username="nuevo").exists()


@pytest.mark.django_db
def test_crear_usuario_respeta_limite_del_plan(
    admin_a, clinica_configurada
):
    plan = PlanSuscripcion.objects.create(
        nombre="Plan Uno", precio=Decimal("1.00"), max_usuarios=1
    )
    crear_suscripcion(clinica_configurada, plan)

    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL, _payload_usuario(), format="json"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "limite_usuarios"
    assert respuesta.json()["detalles"]["max_usuarios"] == 1


@pytest.mark.django_db
def test_crear_usuario_con_password_invalida(
    admin_a, suscripcion_amplia
):
    payload = _payload_usuario()
    payload["password"] = "123"

    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL, payload, format="json"
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "password_invalida"


@pytest.mark.django_db
def test_crear_usuario_con_rol_de_otra_clinica(
    admin_a, admin_b, suscripcion_amplia
):
    rol_ajeno = Rol.all_objects.get(
        clinica=admin_b.clinica_id, nombre=ROL_MEDICO
    )

    respuesta = cliente_autenticado(admin_a).post(
        USUARIOS_URL,
        _payload_usuario(roles=[rol_ajeno.pk]),
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


@pytest.mark.django_db
def test_actualizar_email_y_desactivar_usuario(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "objetivo")
    autenticado = cliente_autenticado(admin_a)

    actualizado = autenticado.patch(
        f"{USUARIOS_URL}{usuario.pk}/",
        {"email": "nuevo_email@clinica.local"},
        format="json",
    )
    assert actualizado.status_code == 200
    usuario.refresh_from_db()
    assert usuario.email == "nuevo_email@clinica.local"

    eliminado = autenticado.delete(f"{USUARIOS_URL}{usuario.pk}/")
    assert eliminado.status_code == 204
    usuario.refresh_from_db()
    assert usuario.estado is False


@pytest.mark.django_db
def test_no_desactivar_al_ultimo_administrador(
    admin_a, suscripcion_amplia
):
    respuesta = cliente_autenticado(admin_a).delete(
        f"{USUARIOS_URL}{admin_a.pk}/"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "ultimo_administrador"


@pytest.mark.django_db
def test_reactivar_usuario_valida_capacidad(
    admin_a, clinica_configurada
):
    plan = PlanSuscripcion.objects.create(
        nombre="Plan Dos", precio=Decimal("1.00"), max_usuarios=2
    )
    crear_suscripcion(clinica_configurada, plan)
    usuario = crear_usuario_con_rol(
        clinica_configurada, "inactivo", estado=False
    )
    otro = crear_usuario_con_rol(clinica_configurada, "activo")

    # admin_a + otro = 2 activos; reactivar a "inactivo" excede el plan.
    assert otro.estado is True

    respuesta = cliente_autenticado(admin_a).patch(
        f"{USUARIOS_URL}{usuario.pk}/", {"estado": True}, format="json"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "limite_usuarios"


@pytest.mark.django_db
def test_medico_no_puede_gestionar_usuarios(
    medico_a, suscripcion_amplia
):
    respuesta = cliente_autenticado(medico_a).get(USUARIOS_URL)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_crear_rol_custom_y_duplicado(admin_a, suscripcion_amplia):
    autenticado = cliente_autenticado(admin_a)
    payload = {"nombre": "Recepcionista Senior", "descripcion": "Rol custom."}

    creado = autenticado.post(ROLES_URL, payload, format="json")
    assert creado.status_code == 201
    assert creado.json()["es_base"] is False

    duplicado = autenticado.post(ROLES_URL, payload, format="json")
    assert duplicado.status_code == 409
    assert duplicado.json()["codigo"] == "rol_duplicado"


@pytest.mark.django_db
def test_roles_base_estan_protegidos(
    admin_a, clinica_configurada, suscripcion_amplia
):
    rol = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_ADMIN_CLINICA
    )
    autenticado = cliente_autenticado(admin_a)

    renombrado = autenticado.patch(
        f"{ROLES_URL}{rol.pk}/", {"nombre": "Otro nombre"}, format="json"
    )
    assert renombrado.status_code == 409
    assert renombrado.json()["codigo"] == "rol_base_protegido"

    desactivado = autenticado.patch(
        f"{ROLES_URL}{rol.pk}/", {"estado": False}, format="json"
    )
    assert desactivado.status_code == 409
    assert desactivado.json()["codigo"] == "rol_base_protegido"

    descripcion = autenticado.patch(
        f"{ROLES_URL}{rol.pk}/",
        {"descripcion": "Descripción editable."},
        format="json",
    )
    assert descripcion.status_code == 200
    assert descripcion.json()["descripcion"] == "Descripción editable."

    eliminado = autenticado.delete(f"{ROLES_URL}{rol.pk}/")
    assert eliminado.status_code == 409
    assert eliminado.json()["codigo"] == "rol_base_protegido"


@pytest.mark.django_db
def test_eliminar_rol_con_asignaciones(
    admin_a, clinica_configurada, suscripcion_amplia
):
    rol = Rol.all_objects.create(
        clinica=clinica_configurada, nombre="Temporal"
    )
    usuario = crear_usuario_con_rol(clinica_configurada, "con_rol_temporal")
    UsuarioRol.all_objects.create(usuario=usuario, rol=rol)

    respuesta = cliente_autenticado(admin_a).delete(
        f"{ROLES_URL}{rol.pk}/"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "rol_con_asignaciones"


@pytest.mark.django_db
def test_asignar_y_quitar_rol(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "sin_roles")
    rol = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_MEDICO
    )
    autenticado = cliente_autenticado(admin_a)

    asignado = autenticado.post(
        USUARIO_ROLES_URL,
        {"usuario": usuario.pk, "rol": rol.pk},
        format="json",
    )
    assert asignado.status_code == 201, asignado.json()

    duplicado = autenticado.post(
        USUARIO_ROLES_URL,
        {"usuario": usuario.pk, "rol": rol.pk},
        format="json",
    )
    assert duplicado.status_code == 409
    assert duplicado.json()["codigo"] == "rol_ya_asignado"

    quitado = autenticado.delete(
        f"{USUARIO_ROLES_URL}{asignado.json()['id']}/"
    )
    assert quitado.status_code == 204
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario, rol=rol
    ).exists()


@pytest.mark.django_db
def test_no_quitar_el_ultimo_rol_admin(
    admin_a, clinica_configurada, suscripcion_amplia
):
    asignacion = UsuarioRol.all_objects.get(
        usuario=admin_a, rol__nombre=ROL_ADMIN_CLINICA
    )

    respuesta = cliente_autenticado(admin_a).delete(
        f"{USUARIO_ROLES_URL}{asignacion.pk}/"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "ultimo_administrador"


@pytest.mark.django_db
def test_no_asignar_rol_de_otra_clinica(
    admin_a, admin_b, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "sin_roles")
    rol_ajeno = Rol.all_objects.get(
        clinica=admin_b.clinica_id, nombre=ROL_MEDICO
    )

    respuesta = cliente_autenticado(admin_a).post(
        USUARIO_ROLES_URL,
        {"usuario": usuario.pk, "rol": rol_ajeno.pk},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


@pytest.mark.django_db(transaction=True)
def test_concurrencia_max_usuarios_solo_uno_crea(
    admin_a, clinica_configurada
):
    plan = PlanSuscripcion.objects.create(
        nombre="Plan Concurrencia",
        precio=Decimal("5.00"),
        max_usuarios=2,
    )
    crear_suscripcion(clinica_configurada, plan)
    token = token_para(admin_a)
    barrera = threading.Barrier(2)

    def crear(indice):
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        barrera.wait(timeout=10)
        try:
            respuesta = cliente.post(
                USUARIOS_URL,
                _payload_usuario(username=f"concurrente_{indice}"),
                format="json",
            )
            return respuesta.status_code, respuesta.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(crear, [1, 2]))

    codigos = sorted(resultado[0] for resultado in resultados)
    assert codigos == [201, 409]

    rechazado = next(
        cuerpo for codigo, cuerpo in resultados if codigo == 409
    )
    assert rechazado["codigo"] == "limite_usuarios"
    assert (
        Usuario.all_objects.filter(
            username__startswith="concurrente_"
        ).count()
        == 1
    )
