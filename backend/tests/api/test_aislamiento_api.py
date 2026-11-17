"""Pruebas de aislamiento multitenant en los endpoints del Sprint 1."""

from datetime import date, time

import pytest

from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from apps.seguridad.models import Rol, Usuario, UsuarioRol

from .helpers import cliente_autenticado, crear_personal_medico, crear_usuario_con_rol

PERSONAL_URL = "/api/v1/personal/"
ESPECIALIDADES_URL = "/api/v1/especialidades/"
MEDICOS_URL = "/api/v1/medicos/"
HORARIOS_URL = "/api/v1/horarios/"
USUARIOS_URL = "/api/v1/usuarios/"
ROLES_URL = "/api/v1/roles/"


@pytest.fixture
def recursos_b(db, clinica_b):
    from apps.clinicas.services import (
        crear_especialidades_base,
        crear_roles_base,
    )

    crear_roles_base(clinica_b)
    crear_especialidades_base(clinica_b)
    usuario = crear_usuario_con_rol(clinica_b, "usuario_b_recurso")
    personal, medico = crear_personal_medico(
        clinica_b,
        usuario,
        ci="CI-B-REC",
        colegiatura="COL-B-REC",
    )
    horario = HorarioAtencion.all_objects.create(
        medico=medico,
        dia_semana=0,
        hora_inicio=time(8, 0),
        hora_fin=time(12, 0),
    )
    rol = Rol.all_objects.get(clinica=clinica_b, nombre="Médico")
    asignacion = UsuarioRol.all_objects.create(usuario=usuario, rol=rol)
    return {
        "usuario": usuario,
        "personal": personal,
        "medico": medico,
        "horario": horario,
        "especialidad": medico.especialidad,
        "rol": rol,
        "asignacion": asignacion,
    }


@pytest.mark.django_db
def test_listados_solo_muestran_datos_de_la_propia_clinica(
    admin_a, suscripcion_amplia, recursos_b
):
    autenticado = cliente_autenticado(admin_a)

    casos = [
        (USUARIOS_URL, "usuario"),
        (ROLES_URL, "rol"),
        (PERSONAL_URL, "personal"),
        (ESPECIALIDADES_URL, "especialidad"),
        (MEDICOS_URL, "medico"),
        (HORARIOS_URL, "horario"),
    ]
    for url, clave in casos:
        respuesta = autenticado.get(url)
        assert respuesta.status_code == 200, url
        ids = {item["id"] for item in respuesta.json()["results"]}
        assert recursos_b[clave].pk not in ids, url


@pytest.mark.django_db
def test_detalles_de_otra_clinica_devuelven_404(
    admin_a, suscripcion_amplia, recursos_b
):
    autenticado = cliente_autenticado(admin_a)

    casos = [
        (USUARIOS_URL, recursos_b["usuario"].pk),
        (ROLES_URL, recursos_b["rol"].pk),
        (PERSONAL_URL, recursos_b["personal"].pk),
        (ESPECIALIDADES_URL, recursos_b["especialidad"].pk),
        (MEDICOS_URL, recursos_b["medico"].pk),
        (HORARIOS_URL, recursos_b["horario"].pk),
    ]
    for url, pk in casos:
        respuesta = autenticado.get(f"{url}{pk}/")
        assert respuesta.status_code == 404, url
        assert respuesta.json()["codigo"] == "no_encontrado", url


@pytest.mark.django_db
def test_no_actualizar_ni_eliminar_recursos_de_otra_clinica(
    admin_a, suscripcion_amplia, recursos_b
):
    autenticado = cliente_autenticado(admin_a)

    intentos_patch = [
        (
            f"{USUARIOS_URL}{recursos_b['usuario'].pk}/",
            {"email": "hackeado@clinica.local"},
        ),
        (
            f"{ROLES_URL}{recursos_b['rol'].pk}/",
            {"descripcion": "Rol hackeado"},
        ),
        (
            f"{PERSONAL_URL}{recursos_b['personal'].pk}/",
            {"nombre": "Hackeado"},
        ),
        (
            f"{ESPECIALIDADES_URL}{recursos_b['especialidad'].pk}/",
            {"nombre": "Hackeada"},
        ),
        (
            f"{MEDICOS_URL}{recursos_b['medico'].pk}/",
            {"numero_colegiatura": "COL-HACK"},
        ),
        (
            f"{HORARIOS_URL}{recursos_b['horario'].pk}/",
            {"hora_fin": "13:00"},
        ),
    ]
    for url, payload in intentos_patch:
        respuesta = autenticado.patch(url, payload, format="json")
        assert respuesta.status_code == 404, url
        assert respuesta.json()["codigo"] == "no_encontrado", url

    intentos_delete = [
        f"{USUARIOS_URL}{recursos_b['usuario'].pk}/",
        f"{ROLES_URL}{recursos_b['rol'].pk}/",
        f"{PERSONAL_URL}{recursos_b['personal'].pk}/",
        f"{ESPECIALIDADES_URL}{recursos_b['especialidad'].pk}/",
        f"{MEDICOS_URL}{recursos_b['medico'].pk}/",
        f"{HORARIOS_URL}{recursos_b['horario'].pk}/",
        f"/api/v1/usuario-roles/{recursos_b['asignacion'].pk}/",
    ]
    for url in intentos_delete:
        respuesta = autenticado.delete(url)
        assert respuesta.status_code == 404, url
        assert respuesta.json()["codigo"] == "no_encontrado", url

    recursos_b["usuario"].refresh_from_db()
    assert recursos_b["usuario"].email != "hackeado@clinica.local"
    recursos_b["rol"].refresh_from_db()
    assert recursos_b["rol"].descripcion != "Rol hackeado"
    recursos_b["personal"].refresh_from_db()
    assert recursos_b["personal"].nombre != "Hackeado"
    recursos_b["especialidad"].refresh_from_db()
    assert recursos_b["especialidad"].nombre != "Hackeada"
    recursos_b["medico"].refresh_from_db()
    assert recursos_b["medico"].numero_colegiatura != "COL-HACK"
    recursos_b["horario"].refresh_from_db()
    assert recursos_b["horario"].hora_fin != time(13, 0)
    assert UsuarioRol.all_objects.filter(
        pk=recursos_b["asignacion"].pk
    ).exists()


@pytest.mark.django_db
def test_no_crear_medico_con_relaciones_de_otra_clinica(
    admin_a, clinica_configurada, suscripcion_amplia, recursos_b
):
    autenticado = cliente_autenticado(admin_a)
    especialidad_a = Especialidad.all_objects.filter(
        clinica=clinica_configurada
    ).first()
    personal_a = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="CI-A-MED",
        nombre="Personal",
        apellido="Local",
        telefono="70000000",
        cargo="MEDICO",
        fecha_ingreso=date(2024, 1, 1),
    )

    personal_ajeno = autenticado.post(
        MEDICOS_URL,
        {
            "personal": recursos_b["personal"].pk,
            "especialidad": especialidad_a.pk,
            "numero_colegiatura": "COL-A-X1",
        },
        format="json",
    )
    assert personal_ajeno.status_code == 400
    assert personal_ajeno.json()["codigo"] == "datos_invalidos"

    especialidad_ajena = autenticado.post(
        MEDICOS_URL,
        {
            "personal": personal_a.pk,
            "especialidad": recursos_b["especialidad"].pk,
            "numero_colegiatura": "COL-A-X2",
        },
        format="json",
    )
    assert especialidad_ajena.status_code == 400
    assert especialidad_ajena.json()["codigo"] == "datos_invalidos"
    assert not Medico.all_objects.filter(
        numero_colegiatura__startswith="COL-A-X"
    ).exists()


@pytest.mark.django_db
def test_no_crear_horario_con_medico_de_otra_clinica(
    admin_a, suscripcion_amplia, recursos_b
):
    respuesta = cliente_autenticado(admin_a).post(
        HORARIOS_URL,
        {
            "medico": recursos_b["medico"].pk,
            "dia_semana": 1,
            "hora_inicio": "08:00",
            "hora_fin": "10:00",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert not HorarioAtencion.all_objects.filter(
        medico=recursos_b["medico"], dia_semana=1
    ).exists()


@pytest.mark.django_db
def test_no_crear_personal_vinculado_a_usuario_de_otra_clinica(
    admin_a, suscripcion_amplia, recursos_b
):
    respuesta = cliente_autenticado(admin_a).post(
        PERSONAL_URL,
        {
            "usuario": recursos_b["usuario"].pk,
            "ci": "CI-A-X",
            "nombre": "Cruzado",
            "apellido": "Tenant",
            "telefono": "70000000",
            "cargo": "OTRO",
            "fecha_ingreso": str(date(2024, 1, 1)),
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert not Personal.all_objects.filter(ci="CI-A-X").exists()


@pytest.mark.django_db
def test_no_inyectar_clinica_en_el_cuerpo_de_personal(
    admin_a, clinica_b, suscripcion_amplia
):
    respuesta = cliente_autenticado(admin_a).post(
        PERSONAL_URL,
        {
            "clinica": clinica_b.pk,
            "ci": "CI-A-INYECTADA",
            "nombre": "Inyectada",
            "apellido": "Clínica",
            "telefono": "70000000",
            "cargo": "OTRO",
            "fecha_ingreso": str(date(2024, 1, 1)),
        },
        format="json",
    )

    assert respuesta.status_code == 201
    creado = Personal.all_objects.get(ci="CI-A-INYECTADA")
    assert creado.clinica_id == admin_a.clinica_id
