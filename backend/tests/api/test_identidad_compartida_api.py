"""Identidad compartida entre los perfiles Personal y Paciente."""

from datetime import date

import pytest

from apps.pacientes.models import Paciente
from apps.personal.models import Personal
from apps.core.seed_data import ROL_PACIENTE, ROL_RECEPCIONISTA
from apps.seguridad.models import UsuarioRol

from .helpers import cliente_autenticado, crear_usuario_con_rol


def datos_personal(ci, **cambios):
    datos = {
        "ci": ci,
        "nombre": "Nombre enviado",
        "apellido": "Apellido enviado",
        "telefono": "111111",
        "cargo": "OTRO",
        "fecha_ingreso": "2026-01-01",
    }
    datos.update(cambios)
    return datos


def datos_paciente(ci, **cambios):
    datos = {
        "ci": ci,
        "nombre": "Nombre enviado",
        "apellido": "Apellido enviado",
        "telefono": "111111",
        "sexo": "OTRO",
        "fecha_nacimiento": "1990-01-01",
        "email": "persona@example.com",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_crear_personal_reutiliza_identidad_del_paciente(
    admin_a, suscripcion_amplia
):
    Paciente.all_objects.create(
        clinica=admin_a.clinica,
        ci="CI-COMPARTIDA-1",
        nombre="Ana",
        apellido="Correcta",
        telefono="70000001",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
    )

    respuesta = cliente_autenticado(admin_a).post(
        "/api/v1/personal/",
        datos_personal("CI-COMPARTIDA-1"),
        format="json",
    )

    assert respuesta.status_code == 201, respuesta.data
    assert respuesta.data["nombre"] == "Ana"
    assert respuesta.data["apellido"] == "Correcta"
    assert respuesta.data["telefono"] == "70000001"


@pytest.mark.django_db
def test_crear_paciente_reutiliza_identidad_del_personal(
    admin_a, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        admin_a.clinica,
        "luis_identidad",
        ROL_RECEPCIONISTA,
        email="luis.verificado@example.com",
    )
    Personal.all_objects.create(
        clinica=admin_a.clinica,
        usuario=usuario,
        ci="CI-COMPARTIDA-2",
        nombre="Luis",
        apellido="Verificado",
        telefono="70000002",
        cargo="OTRO",
        fecha_ingreso=date(2026, 1, 1),
    )

    cliente = cliente_autenticado(admin_a)
    identidad = cliente.get(
        "/api/v1/pacientes/identidad-por-ci/",
        {"ci": "CI-COMPARTIDA-2"},
    )
    respuesta = cliente.post(
        "/api/v1/pacientes/",
        datos_paciente("CI-COMPARTIDA-2"),
        format="json",
    )

    assert identidad.status_code == 200
    assert identidad.data["email"] == "luis.verificado@example.com"
    assert respuesta.status_code == 201, respuesta.data
    assert respuesta.data["nombre"] == "Luis"
    assert respuesta.data["apellido"] == "Verificado"
    assert respuesta.data["telefono"] == "70000002"
    assert respuesta.data["email"] == "luis.verificado@example.com"
    paciente = Paciente.all_objects.get(clinica=admin_a.clinica, ci="CI-COMPARTIDA-2")
    assert paciente.usuario_id == usuario.pk
    assert set(
        UsuarioRol.all_objects.filter(usuario=usuario)
        .values_list("rol__nombre", flat=True)
    ) == {ROL_RECEPCIONISTA, ROL_PACIENTE}


@pytest.mark.django_db
@pytest.mark.parametrize("origen", ["personal", "paciente"])
def test_editar_un_perfil_sincroniza_nombre_apellido_y_telefono(
    admin_a, suscripcion_amplia, origen
):
    personal = Personal.all_objects.create(
        clinica=admin_a.clinica,
        ci="CI-SINCRONIZADA",
        nombre="Inicial",
        apellido="Persona",
        telefono="70000003",
        cargo="OTRO",
        fecha_ingreso=date(2026, 1, 1),
    )
    paciente = Paciente.all_objects.create(
        clinica=admin_a.clinica,
        ci=personal.ci,
        nombre=personal.nombre,
        apellido=personal.apellido,
        telefono=personal.telefono,
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
    )
    cliente = cliente_autenticado(admin_a)
    if origen == "personal":
        url = f"/api/v1/personal/{personal.pk}/"
    else:
        url = f"/api/v1/pacientes/{paciente.pk}/"

    respuesta = cliente.patch(
        url,
        {
            "nombre": "Nombre nuevo",
            "apellido": "Apellido nuevo",
            "telefono": "79999999",
        },
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
    personal.refresh_from_db()
    paciente.refresh_from_db()
    esperado = ("Nombre nuevo", "Apellido nuevo", "79999999")
    assert (personal.nombre, personal.apellido, personal.telefono) == esperado
    assert (paciente.nombre, paciente.apellido, paciente.telefono) == esperado


@pytest.mark.django_db
def test_consulta_identidad_es_exacta_y_aislada_por_clinica(
    admin_a, clinica_b, suscripcion_amplia
):
    Paciente.all_objects.create(
        clinica=admin_a.clinica,
        ci="CI-BUSCADA",
        nombre="Visible",
        apellido="Local",
        telefono="70000004",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
    )
    Personal.all_objects.create(
        clinica=clinica_b,
        ci="CI-AJENA",
        nombre="No",
        apellido="Visible",
        telefono="70000005",
        cargo="OTRO",
        fecha_ingreso=date(2026, 1, 1),
    )
    cliente = cliente_autenticado(admin_a)

    encontrada = cliente.get(
        "/api/v1/personal/identidad-por-ci/", {"ci": "CI-BUSCADA"}
    )
    ajena = cliente.get(
        "/api/v1/pacientes/identidad-por-ci/", {"ci": "CI-AJENA"}
    )

    assert encontrada.status_code == 200
    assert encontrada.data == {
        "encontrado": True,
        "ci": "CI-BUSCADA",
        "nombre": "Visible",
        "apellido": "Local",
        "telefono": "70000004",
        "email": "",
        "origen": "PACIENTE",
    }
    assert ajena.status_code == 200
    assert ajena.data["encontrado"] is False


@pytest.mark.django_db
def test_ci_no_se_modifica_despues_del_registro(admin_a, suscripcion_amplia):
    personal = Personal.all_objects.create(
        clinica=admin_a.clinica,
        ci="CI-INMUTABLE",
        nombre="CI",
        apellido="Estable",
        telefono="70000006",
        cargo="OTRO",
        fecha_ingreso=date(2026, 1, 1),
    )

    respuesta = cliente_autenticado(admin_a).patch(
        f"/api/v1/personal/{personal.pk}/",
        {"ci": "OTRA-CI"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "ci_no_modificable"


@pytest.mark.django_db
def test_editar_correo_de_usuario_sincroniza_paciente_por_identidad(
    admin_a, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        admin_a.clinica,
        "correo_compartido",
        email="correo.inicial@example.com",
    )
    Personal.all_objects.create(
        clinica=admin_a.clinica,
        usuario=usuario,
        ci="CI-CORREO",
        nombre="Correo",
        apellido="Compartido",
        telefono="70000007",
        cargo="OTRO",
        fecha_ingreso=date(2026, 1, 1),
    )
    paciente = Paciente.all_objects.create(
        clinica=admin_a.clinica,
        ci="CI-CORREO",
        nombre="Correo",
        apellido="Compartido",
        telefono="70000007",
        email="correo.diferente@example.com",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
    )

    respuesta = cliente_autenticado(admin_a).patch(
        f"/api/v1/usuarios/{usuario.pk}/",
        {"email": "correo.nuevo@example.com"},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
    paciente.refresh_from_db()
    assert paciente.email == "correo.nuevo@example.com"
