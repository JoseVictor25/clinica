"""Pruebas de personal, especialidades, médicos y horarios."""

from datetime import date, time

import pytest
from django.utils import timezone

from apps.atencion.models import Cita, Consulta, Receta
from apps.core.seed_data import ROL_MEDICO
from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from apps.pacientes.models import Paciente
from apps.seguridad.models import UsuarioRol

from .helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)

PERSONAL_URL = "/api/v1/personal/"
ESPECIALIDADES_URL = "/api/v1/especialidades/"
MEDICOS_URL = "/api/v1/medicos/"
HORARIOS_URL = "/api/v1/horarios/"


def _payload_personal(ci="CI-001", nombre="Ana", apellido="Pérez"):
    return {
        "ci": ci,
        "nombre": nombre,
        "apellido": apellido,
        "telefono": "70000001",
        "cargo": "MEDICO",
        "fecha_ingreso": str(date(2024, 1, 1)),
    }


def _payload_horario(medico_id, inicio="08:00", fin="12:00", dia=0):
    return {
        "medico": medico_id,
        "dia_semana": dia,
        "hora_inicio": inicio,
        "hora_fin": fin,
    }


# --- Personal ---------------------------------------------------------------


@pytest.mark.django_db
def test_admin_crea_personal(admin_a, suscripcion_amplia):
    respuesta = cliente_autenticado(admin_a).post(
        PERSONAL_URL, _payload_personal(), format="json"
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["clinica"] == admin_a.clinica_id
    assert Personal.all_objects.filter(
        clinica=admin_a.clinica_id, ci="CI-001"
    ).exists()


@pytest.mark.django_db
def test_personal_ci_duplicada(admin_a, suscripcion_amplia):
    autenticado = cliente_autenticado(admin_a)
    assert (
        autenticado.post(
            PERSONAL_URL, _payload_personal(), format="json"
        ).status_code
        == 201
    )

    duplicado = autenticado.post(
        PERSONAL_URL, _payload_personal(), format="json"
    )

    assert duplicado.status_code == 409
    assert duplicado.json()["codigo"] == "ci_duplicada"


@pytest.mark.django_db
def test_finalizar_medico_conserva_identidad_e_historial(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_vinculado", ROL_MEDICO
    )
    personal, medico = crear_personal_medico(clinica_configurada, usuario)
    paciente = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="CI-HISTORIAL-BAJA",
        nombre="Paciente",
        apellido="Historial",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000002",
    )
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente,
        fecha=timezone.localdate(),
        hora=time(9, 0),
        motivo="Control",
    )
    consulta = Consulta.all_objects.create(
        clinica=clinica_configurada,
        cita=cita,
        medico=medico,
        paciente=paciente,
        motivo="Control",
        observacion="Sin novedad",
        diagnostico="Estable",
    )
    receta = Receta.all_objects.create(
        consulta=consulta,
        indicaciones="Conservar seguimiento",
    )

    respuesta = cliente_autenticado(admin_a).delete(
        f"{PERSONAL_URL}{personal.pk}/"
    )

    assert respuesta.status_code == 204
    personal.refresh_from_db()
    medico.refresh_from_db()
    usuario.refresh_from_db()
    assert personal.estado is False
    assert personal.usuario_id == usuario.pk
    assert medico.estado is False
    assert usuario.estado is False
    assert Personal.all_objects.filter(pk=personal.pk).exists()
    assert Medico.all_objects.filter(pk=medico.pk).exists()
    assert Cita.all_objects.filter(pk=cita.pk, medico=medico).exists()
    assert Consulta.all_objects.filter(pk=consulta.pk, medico=medico).exists()
    assert Receta.all_objects.filter(pk=receta.pk, consulta=consulta).exists()


@pytest.mark.django_db
def test_reactivar_personal_restaura_cuenta_rol_y_medico(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_reactivado", ROL_MEDICO
    )
    personal, medico = crear_personal_medico(
        clinica_configurada,
        usuario,
        ci="CI-REACTIVAR",
        colegiatura="COL-REACTIVAR",
    )
    cliente = cliente_autenticado(admin_a)
    assert cliente.delete(f"{PERSONAL_URL}{personal.pk}/").status_code == 204

    respuesta = cliente.patch(
        f"{PERSONAL_URL}{personal.pk}/",
        {"estado": True},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.json()
    personal.refresh_from_db()
    medico.refresh_from_db()
    usuario.refresh_from_db()
    assert personal.estado is True
    assert medico.estado is True
    assert usuario.estado is True
    assert UsuarioRol.all_objects.filter(
        usuario=usuario,
        rol__nombre=ROL_MEDICO,
    ).exists()


@pytest.mark.django_db
def test_medico_no_puede_crear_personal(medico_a, suscripcion_amplia):
    respuesta = cliente_autenticado(medico_a).post(
        PERSONAL_URL, _payload_personal(), format="json"
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_vinculo_usuario_personal_es_permanente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        **_payload_personal(),
    )
    usuario = crear_usuario_con_rol(clinica_configurada, "a_vincular")
    Paciente.all_objects.create(
        clinica=clinica_configurada,
        usuario=usuario,
        ci=personal.ci,
        nombre="Ana",
        apellido="Pérez",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000001",
    )
    autenticado = cliente_autenticado(admin_a)

    vinculado = autenticado.post(
        f"{PERSONAL_URL}{personal.pk}/vincular-usuario/",
        {"usuario_id": usuario.pk},
        format="json",
    )
    assert vinculado.status_code == 200
    assert vinculado.json()["usuario"] == usuario.pk

    desvinculado = autenticado.post(
        f"{PERSONAL_URL}{personal.pk}/vincular-usuario/",
        {"usuario_id": None},
        format="json",
    )
    assert desvinculado.status_code == 409
    assert desvinculado.json()["codigo"] == "vinculo_personal_permanente"
    personal.refresh_from_db()
    assert personal.usuario_id == usuario.pk


@pytest.mark.django_db
def test_usuario_ya_vinculado_a_otro_personal(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "ya_vinculado")
    Personal.all_objects.create(
        clinica=clinica_configurada,
        usuario=usuario,
        ci="CI-VINCULADO",
        nombre="Uno",
        apellido="Vinculado",
        telefono="70000001",
        cargo="OTRO",
        fecha_ingreso=date(2024, 1, 1),
    )
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="CI-NUEVO",
        nombre="Dos",
        apellido="Nuevo",
        telefono="70000002",
        cargo="OTRO",
        fecha_ingreso=date(2024, 1, 1),
    )

    respuesta = cliente_autenticado(admin_a).post(
        f"{PERSONAL_URL}{personal.pk}/vincular-usuario/",
        {"usuario_id": usuario.pk},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "usuario_ya_vinculado"


# --- Especialidades ---------------------------------------------------------


@pytest.mark.django_db
def test_especialidad_crud_y_duplicada(admin_a, suscripcion_amplia):
    autenticado = cliente_autenticado(admin_a)
    payload = {"nombre": "Nutrición", "descripcion": "Nutrición clínica."}

    creada = autenticado.post(ESPECIALIDADES_URL, payload, format="json")
    assert creada.status_code == 201

    duplicada = autenticado.post(ESPECIALIDADES_URL, payload, format="json")
    assert duplicada.status_code == 409
    assert duplicada.json()["codigo"] == "especialidad_duplicada"


@pytest.mark.django_db
def test_medico_solo_ve_sus_especialidades_asignadas(
    medico_a, clinica_configurada, suscripcion_amplia
):
    _, medico = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="CI-ESP-001",
        colegiatura="COL-ESP-001",
    )
    adicional = Especialidad.all_objects.create(
        clinica=clinica_configurada,
        nombre="Medicina interna",
        descripcion="Especialidad adicional.",
    )
    no_asignada = Especialidad.all_objects.create(
        clinica=clinica_configurada,
        nombre="Oncología",
        descripcion="No asignada al médico.",
    )
    medico.especialidades.add(medico.especialidad, adicional)
    autenticado = cliente_autenticado(medico_a)

    respuesta = autenticado.get(ESPECIALIDADES_URL)
    assert respuesta.status_code == 200
    assert {item["id"] for item in respuesta.json()["results"]} == {
        medico.especialidad_id,
        adicional.pk,
    }
    assert (
        autenticado.get(f"{ESPECIALIDADES_URL}{no_asignada.pk}/").status_code
        == 404
    )
    assert (
        autenticado.post(
            ESPECIALIDADES_URL, {"nombre": "Nueva"}, format="json"
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_no_eliminar_especialidad_en_uso(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "medico_uso")
    _, medico = crear_personal_medico(clinica_configurada, usuario)

    respuesta = cliente_autenticado(admin_a).delete(
        f"{ESPECIALIDADES_URL}{medico.especialidad_id}/"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "especialidad_en_uso"


# --- Médicos ----------------------------------------------------------------


@pytest.mark.django_db
def test_admin_crea_medico(admin_a, clinica_configurada, suscripcion_amplia):
    personal = Personal.all_objects.create(
        clinica=clinica_configurada, **_payload_personal(ci="CI-MED-100")
    )
    especialidad = Especialidad.all_objects.filter(
        clinica=clinica_configurada
    ).first()
    adicional = Especialidad.all_objects.create(
        clinica=clinica_configurada,
        nombre="Medicina deportiva",
        descripcion="Especialidad adicional.",
    )

    respuesta = cliente_autenticado(admin_a).post(
        MEDICOS_URL,
        {
            "personal": personal.pk,
            "especialidad": especialidad.pk,
            "especialidades": [especialidad.pk, adicional.pk],
            "numero_colegiatura": "COL-100",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["clinica"] == admin_a.clinica_id
    assert set(respuesta.json()["especialidades"]) == {
        especialidad.pk,
        adicional.pk,
    }
    assert Medico.all_objects.filter(
        numero_colegiatura="COL-100"
    ).exists()


@pytest.mark.django_db
def test_no_reutilizar_personal_ni_colegiatura(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "medico_uno")
    personal, medico = crear_personal_medico(
        clinica_configurada, usuario, ci="CI-MED-101", colegiatura="COL-101"
    )
    otro_personal = Personal.all_objects.create(
        clinica=clinica_configurada, **_payload_personal(ci="CI-MED-102")
    )
    autenticado = cliente_autenticado(admin_a)

    mismo_personal = autenticado.post(
        MEDICOS_URL,
        {
            "personal": personal.pk,
            "especialidad": medico.especialidad_id,
            "numero_colegiatura": "COL-102",
        },
        format="json",
    )
    assert mismo_personal.status_code == 409
    assert mismo_personal.json()["codigo"] == "personal_ya_es_medico"

    misma_colegiatura = autenticado.post(
        MEDICOS_URL,
        {
            "personal": otro_personal.pk,
            "especialidad": medico.especialidad_id,
            "numero_colegiatura": "COL-101",
        },
        format="json",
    )
    assert misma_colegiatura.status_code == 409
    assert misma_colegiatura.json()["codigo"] == "colegiatura_duplicada"


@pytest.mark.django_db
def test_medico_sin_personal_vinculado_recibe_listas_vacias(
    medico_a, suscripcion_amplia
):
    autenticado = cliente_autenticado(medico_a)

    medicos = autenticado.get(MEDICOS_URL)
    horarios = autenticado.get(HORARIOS_URL)

    assert medicos.status_code == 200
    assert medicos.json()["results"] == []
    assert horarios.status_code == 200
    assert horarios.json()["results"] == []


@pytest.mark.django_db
def test_medico_solo_ve_su_propio_perfil_y_horarios(
    medico_a, clinica_configurada, suscripcion_amplia, admin_a
):
    _, medico_propio = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="CI-MED-A",
        colegiatura="COL-A",
    )
    otro_usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_b", ROL_MEDICO
    )
    _, medico_ajeno = crear_personal_medico(
        clinica_configurada,
        otro_usuario,
        ci="CI-MED-B",
        colegiatura="COL-B",
    )
    HorarioAtencion.all_objects.create(
        medico=medico_propio,
        dia_semana=0,
        hora_inicio=time(8, 0),
        hora_fin=time(12, 0),
    )
    HorarioAtencion.all_objects.create(
        medico=medico_ajeno,
        dia_semana=1,
        hora_inicio=time(8, 0),
        hora_fin=time(12, 0),
    )
    autenticado = cliente_autenticado(medico_a)

    medicos = autenticado.get(MEDICOS_URL).json()["results"]
    assert [item["id"] for item in medicos] == [medico_propio.pk]

    horarios = autenticado.get(HORARIOS_URL).json()["results"]
    assert len(horarios) == 1
    assert horarios[0]["medico"] == medico_propio.pk

    ajeno = autenticado.get(f"{MEDICOS_URL}{medico_ajeno.pk}/")
    assert ajeno.status_code == 404


# --- Horarios ---------------------------------------------------------------


@pytest.mark.django_db
def test_admin_crea_horario_y_requiere_medico(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "medico_horario")
    _, medico = crear_personal_medico(
        clinica_configurada, usuario, ci="CI-H-001", colegiatura="COL-H-001"
    )
    autenticado = cliente_autenticado(admin_a)

    creado = autenticado.post(
        HORARIOS_URL, _payload_horario(medico.pk), format="json"
    )
    assert creado.status_code == 201

    sin_medico = autenticado.post(
        HORARIOS_URL,
        {"dia_semana": 1, "hora_inicio": "08:00", "hora_fin": "12:00"},
        format="json",
    )
    assert sin_medico.status_code == 400
    assert sin_medico.json()["codigo"] == "medico_requerido"


@pytest.mark.django_db
def test_horario_invalido_y_solapado(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "medico_horario")
    _, medico = crear_personal_medico(
        clinica_configurada, usuario, ci="CI-H-002", colegiatura="COL-H-002"
    )
    autenticado = cliente_autenticado(admin_a)

    invalido = autenticado.post(
        HORARIOS_URL,
        _payload_horario(medico.pk, inicio="12:00", fin="08:00"),
        format="json",
    )
    assert invalido.status_code == 400
    assert invalido.json()["codigo"] == "datos_invalidos"

    assert (
        autenticado.post(
            HORARIOS_URL, _payload_horario(medico.pk), format="json"
        ).status_code
        == 201
    )
    solapado = autenticado.post(
        HORARIOS_URL,
        _payload_horario(medico.pk, inicio="10:00", fin="14:00"),
        format="json",
    )
    assert solapado.status_code == 409
    assert solapado.json()["codigo"] == "horario_solapado"


@pytest.mark.django_db
def test_medico_crea_su_propio_horario_sin_enviar_medico(
    medico_a, clinica_configurada, suscripcion_amplia
):
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="CI-H-003", colegiatura="COL-H-003"
    )

    respuesta = cliente_autenticado(medico_a).post(
        HORARIOS_URL,
        {"dia_semana": 2, "hora_inicio": "09:00", "hora_fin": "11:00"},
        format="json",
    )

    assert respuesta.status_code == 201, respuesta.json()
    assert respuesta.json()["medico"] == medico.pk


@pytest.mark.django_db
def test_medico_sin_vinculo_no_puede_crear_horario(
    medico_a, suscripcion_amplia
):
    respuesta = cliente_autenticado(medico_a).post(
        HORARIOS_URL,
        {"dia_semana": 2, "hora_inicio": "09:00", "hora_fin": "11:00"},
        format="json",
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "medico_no_vinculado"
