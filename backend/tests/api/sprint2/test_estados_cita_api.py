"""Pruebas API de S2-07: confirmar, cancelar y reprogramar citas."""

from datetime import date, time
import json
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.test import Client

from apps.atencion.models import Cita, EstadoCita
from apps.pacientes.models import Paciente
from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from tests.api.helpers import cliente_autenticado


URL = "/api/v1/citas/"
NUEVA_FECHA = "2026-11-16"
NUEVA_HORA = "08:30"


@pytest.fixture
def cita_estado(clinica_configurada, paciente_a, medico_citas, horario_lunes):
    return Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=date(2026, 11, 16),
        hora=time(8),
        motivo="Control original",
    )


def accion(cita, nombre):
    return f"{URL}{cita.pk}/{nombre}/"


@pytest.mark.django_db
@pytest.mark.parametrize("usuario_fixture", ["admin_a", "recepcionista_a"])
def test_roles_autorizados_confirman(request, usuario_fixture, suscripcion_amplia, cita_estado):
    usuario = request.getfixturevalue(usuario_fixture)
    respuesta = cliente_autenticado(usuario).post(
        accion(cita_estado, "confirmar"), {}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == EstadoCita.CONFIRMADA
    cita_estado.refresh_from_db()
    assert cita_estado.estado == EstadoCita.CONFIRMADA
    assert cita_estado.motivo == "Control original"


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA])
def test_cancelar_transiciones_permitidas(admin_a, suscripcion_amplia, cita_estado, estado):
    cita_estado.estado = estado
    cita_estado.save(update_fields=["estado"])
    originales = (
        cita_estado.clinica_id,
        cita_estado.paciente_id,
        cita_estado.medico_id,
        cita_estado.fecha,
        cita_estado.hora,
        cita_estado.motivo,
    )

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "cancelar"), {}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == EstadoCita.CANCELADA
    cita_estado.refresh_from_db()
    assert cita_estado.estado == EstadoCita.CANCELADA
    assert (
        cita_estado.clinica_id,
        cita_estado.paciente_id,
        cita_estado.medico_id,
        cita_estado.fecha,
        cita_estado.hora,
        cita_estado.motivo,
    ) == originales


@pytest.mark.django_db
def test_confirmar_acepta_ausencia_de_cuerpo(admin_a, suscripcion_amplia, cita_estado):
    respuesta = cliente_autenticado(admin_a).post(accion(cita_estado, "confirmar"))
    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == EstadoCita.CONFIRMADA


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("nombre", "estado"),
    [
        ("confirmar", EstadoCita.CONFIRMADA),
        ("confirmar", EstadoCita.ATENDIDA),
        ("confirmar", EstadoCita.CANCELADA),
        ("confirmar", EstadoCita.NO_ASISTIO),
        ("cancelar", EstadoCita.ATENDIDA),
        ("cancelar", EstadoCita.CANCELADA),
        ("cancelar", EstadoCita.NO_ASISTIO),
    ],
)
def test_transiciones_invalidas_no_modifican_cita(
    admin_a, suscripcion_amplia, cita_estado, nombre, estado
):
    cita_estado.estado = estado
    cita_estado.save(update_fields=["estado"])

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, nombre), {}, format="json"
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "transicion_cita_invalida"
    cita_estado.refresh_from_db()
    assert cita_estado.estado == estado


@pytest.mark.django_db
@pytest.mark.parametrize("nombre", ["confirmar", "cancelar"])
def test_acciones_sin_parametros_rechazan_campos(
    admin_a, suscripcion_amplia, cita_estado, nombre
):
    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, nombre), {"estado": "CANCELADA"}, format="json"
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert "estado" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_cancelar_pasada_y_con_participantes_inactivos(
    admin_a, suscripcion_amplia, cita_estado
):
    cita_estado.fecha = date(2026, 11, 15)
    cita_estado.paciente.estado = False
    cita_estado.medico.estado = False
    cita_estado.medico.personal.estado = False
    cita_estado.paciente.save(update_fields=["estado"])
    cita_estado.medico.save(update_fields=["estado"])
    cita_estado.medico.personal.save(update_fields=["estado"])
    cita_estado.save(update_fields=["fecha"])

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "cancelar"), {}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == EstadoCita.CANCELADA


@pytest.mark.django_db
def test_cancelar_libera_el_intervalo(
    admin_a, suscripcion_amplia, cita_estado
):
    cliente = cliente_autenticado(admin_a)
    cancelada = cliente.post(accion(cita_estado, "cancelar"), {}, format="json")
    disponibilidad = cliente.get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": "2026-11-16",
        },
    )

    assert cancelada.status_code == 200
    assert disponibilidad.status_code == 200
    assert "08:00" in disponibilidad.data["horarios"]


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA])
def test_reprogramar_conserva_relaciones_y_deja_programada(
    admin_a, suscripcion_amplia, cita_estado, estado
):
    cita_estado.estado = estado
    cita_estado.save(update_fields=["estado"])
    originales = (
        cita_estado.clinica_id,
        cita_estado.paciente_id,
        cita_estado.medico_id,
        cita_estado.motivo,
    )

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
        format="json",
    )

    assert respuesta.status_code == 200
    cita_estado.refresh_from_db()
    assert cita_estado.fecha == date(2026, 11, 16)
    assert cita_estado.hora == time(8, 30)
    assert cita_estado.estado == EstadoCita.PROGRAMADA
    assert (
        cita_estado.clinica_id,
        cita_estado.paciente_id,
        cita_estado.medico_id,
        cita_estado.motivo,
    ) == originales


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoCita.ATENDIDA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO])
def test_reprogramar_rechaza_estados_terminales(
    admin_a, suscripcion_amplia, cita_estado, estado
):
    cita_estado.estado = estado
    cita_estado.save(update_fields=["estado"])

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cita_no_reprogramable"
    cita_estado.refresh_from_db()
    assert (cita_estado.fecha, cita_estado.hora, cita_estado.estado) == (
        date(2026, 11, 16), time(8), estado
    )


@pytest.mark.django_db
def test_reprogramar_rechaza_mismo_horario_y_hace_rollback(
    admin_a, suscripcion_amplia, cita_estado
):
    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": "2026-11-16", "hora": "08:00"},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cita_no_reprogramable"
    cita_estado.refresh_from_db()
    assert (cita_estado.fecha, cita_estado.hora, cita_estado.estado) == (
        date(2026, 11, 16), time(8), EstadoCita.PROGRAMADA
    )


@pytest.mark.django_db
def test_reprogramar_sin_cambio_no_baja_confirmada_a_programada(
    admin_a, suscripcion_amplia, cita_estado
):
    cita_estado.estado = EstadoCita.CONFIRMADA
    cita_estado.save(update_fields=["estado"])

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": "2026-11-16", "hora": "08:00"},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cita_no_reprogramable"
    cita_estado.refresh_from_db()
    assert (cita_estado.fecha, cita_estado.hora, cita_estado.estado) == (
        date(2026, 11, 16), time(8), EstadoCita.CONFIRMADA
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("datos", "campo"),
    [
        ({"hora": "08:30"}, "fecha"),
        ({"fecha": "2026-11-16"}, "hora"),
        ({"fecha": "16/11/2026", "hora": "08:30"}, "fecha"),
        ({"fecha": "2026-11-16", "hora": "25:00"}, "hora"),
        ({"fecha": None, "hora": "08:30"}, "fecha"),
        ({"fecha": "2026-11-16", "hora": None}, "hora"),
        ({"fecha": "2026-11-16", "hora": "08:30", "paciente_id": 99}, "paciente_id"),
        ({"fecha": "2026-11-16", "hora": "08:30", "medico_id": 99}, "medico_id"),
        ({"fecha": "2026-11-16", "hora": "08:30", "clinica": 1}, "clinica"),
        ({"fecha": "2026-11-16", "hora": "08:30", "clinica_id": 1}, "clinica_id"),
        ({"fecha": "2026-11-16", "hora": "08:30", "estado": "CANCELADA"}, "estado"),
        ({"fecha": "2026-11-16", "hora": "08:30", "motivo": "Cambio"}, "motivo"),
        ({"fecha": "2026-11-16", "hora": "08:30", "especialidad": 1}, "especialidad"),
        ({"fecha": "2026-11-16", "hora": "08:30", "especialidad_id": 1}, "especialidad_id"),
        ({"fecha": "2026-11-16", "hora": "08:30", "duracion": 30}, "duracion"),
        ({"fecha": "2026-11-16", "hora": "08:30", "hora_fin": "09:00"}, "hora_fin"),
    ],
)
def test_reprogramar_valida_contrato(
    admin_a, suscripcion_amplia, cita_estado, datos, campo
):
    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"), datos, format="json"
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("fecha", "hora", "codigo"),
    [
        ("2026-11-15", "08:30", "fecha_cita_pasada"),
        ("2026-11-16", "06:30", "hora_cita_pasada"),
        ("2026-11-16", "07:30", "fuera_horario"),
        ("2026-11-16", "08:15", "fuera_horario"),
        ("2026-11-16", "10:00", "fuera_horario"),
    ],
)
def test_reprogramar_reutiliza_reglas_temporales_y_de_bloques(
    admin_a, suscripcion_amplia, cita_estado, fecha, hora, codigo
):
    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": fecha, "hora": hora},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == codigo
    cita_estado.refresh_from_db()
    assert (cita_estado.fecha, cita_estado.hora) == (date(2026, 11, 16), time(8))


@pytest.mark.django_db
def test_reprogramar_rechaza_pausa_y_bloque_que_supera_hora_fin(
    admin_a, suscripcion_amplia, cita_estado, horario_lunes
):
    horario_lunes.delete()
    HorarioAtencion.all_objects.create(
        medico=cita_estado.medico,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(9, 10),
    )
    HorarioAtencion.all_objects.create(
        medico=cita_estado.medico,
        dia_semana=0,
        hora_inicio=time(10),
        hora_fin=time(11),
    )
    cliente = cliente_autenticado(admin_a)

    supera_fin = cliente.post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": "09:00"},
        format="json",
    )
    pausa = cliente.post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": "09:30"},
        format="json",
    )

    assert supera_fin.status_code == 400
    assert supera_fin.data["codigo"] == "fuera_horario"
    assert pausa.status_code == 400
    assert pausa.data["codigo"] == "fuera_horario"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("recurso", "codigo"),
    [
        ("paciente", "paciente_inactivo"),
        ("medico", "medico_inactivo"),
        ("personal", "medico_inactivo"),
    ],
)
def test_reprogramar_rechaza_participantes_inactivos(
    admin_a, suscripcion_amplia, cita_estado, recurso, codigo
):
    objeto = {
        "paciente": cita_estado.paciente,
        "medico": cita_estado.medico,
        "personal": cita_estado.medico.personal,
    }[recurso]
    objeto.estado = False
    objeto.save(update_fields=["estado"])

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == codigo


@pytest.mark.django_db
def test_reprogramar_reutiliza_validacion_de_disponibilidad_y_hace_rollback(
    admin_a, suscripcion_amplia, cita_estado, clinica_configurada, medico_citas
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-S207-OTRO",
        nombre="Otra",
        apellido="Persona",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000901",
    )
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=otro,
        medico=medico_citas,
        fecha=date(2026, 11, 16),
        hora=time(8, 30),
        motivo="Bloquea destino",
    )

    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "horario_no_disponible"
    cita_estado.refresh_from_db()
    assert (cita_estado.hora, cita_estado.estado) == (time(8), EstadoCita.PROGRAMADA)


@pytest.mark.django_db
@pytest.mark.parametrize("tipo", ["medico", "paciente"])
def test_reprogramar_traduce_restricciones_exactas_y_conserva_transaccion(
    tipo, admin_a, suscripcion_amplia, cita_estado, clinica_configurada, medico_citas
):
    otro_paciente = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci=f"PAC-S207-DB-{tipo}",
        nombre="Restricción",
        apellido="Base de datos",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000905",
    )
    medico_conflicto = medico_citas
    paciente_conflicto = otro_paciente
    esperado = "horario_no_disponible"
    if tipo == "paciente":
        personal = Personal.all_objects.create(
            clinica=clinica_configurada,
            ci="MED-S207-DB-PAC",
            nombre="Otro",
            apellido="Médico",
            telefono="70000906",
            cargo="MEDICO",
            fecha_ingreso=date(2025, 1, 1),
        )
        medico_conflicto = Medico.all_objects.create(
            clinica=clinica_configurada,
            personal=personal,
            especialidad=medico_citas.especialidad,
            numero_colegiatura="COL-S207-DB-PAC",
        )
        paciente_conflicto = cita_estado.paciente
        esperado = "paciente_no_disponible"
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_conflicto,
        medico=medico_conflicto,
        fecha=date(2026, 11, 16),
        hora=time(8, 30),
        motivo="Fuerza restricción exacta",
    )

    with patch("apps.atencion.services._validar_disponibilidad", return_value=None):
        respuesta = cliente_autenticado(admin_a).post(
            accion(cita_estado, "reprogramar"),
            {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
            format="json",
        )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == esperado
    cita_estado.refresh_from_db()
    assert (cita_estado.hora, cita_estado.estado) == (time(8), EstadoCita.PROGRAMADA)
    assert Paciente.all_objects.filter(pk=otro_paciente.pk).exists()


@pytest.mark.django_db
def test_disponibilidad_excluye_solo_la_cita_reprogramada(
    admin_a, suscripcion_amplia, cita_estado, clinica_configurada, medico_citas
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-S207-DISP",
        nombre="Otro",
        apellido="Paciente",
        sexo="M",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000902",
    )
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=otro,
        medico=medico_citas,
        fecha=date(2026, 11, 16),
        hora=time(8, 30),
        motivo="No debe excluirse",
    )

    respuesta = cliente_autenticado(admin_a).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": "2026-11-16",
            "cita_id": cita_estado.pk,
        },
    )

    assert respuesta.status_code == 200
    assert "08:00" in respuesta.data["horarios"]
    assert "08:30" not in respuesta.data["horarios"]


@pytest.mark.django_db
def test_reprogramacion_libera_intervalo_anterior_y_ocupa_nuevo(
    admin_a, suscripcion_amplia, cita_estado
):
    cliente = cliente_autenticado(admin_a)
    reprogramada = cliente.post(
        accion(cita_estado, "reprogramar"),
        {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA},
        format="json",
    )
    disponibilidad = cliente.get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": NUEVA_FECHA,
        },
    )

    assert reprogramada.status_code == 200
    assert "08:00" in disponibilidad.data["horarios"]
    assert "08:30" not in disponibilidad.data["horarios"]


@pytest.mark.django_db
def test_disponibilidad_valida_pertenencia_y_estado_de_cita(
    admin_a, suscripcion_amplia, cita_estado, clinica_configurada, medico_citas
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-S207-MISMATCH",
        nombre="Paciente",
        apellido="Distinto",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000903",
    )
    cliente = cliente_autenticado(admin_a)
    parametros = {
        "paciente_id": otro.pk,
        "medico_id": medico_citas.pk,
        "fecha": "2026-11-16",
        "cita_id": cita_estado.pk,
    }
    distinta = cliente.get(f"{URL}disponibilidad/", parametros)
    assert distinta.status_code == 400
    assert "cita_id" in distinta.data["detalles"]

    cita_estado.estado = EstadoCita.CANCELADA
    cita_estado.save(update_fields=["estado"])
    parametros["paciente_id"] = cita_estado.paciente_id
    terminal = cliente.get(f"{URL}disponibilidad/", parametros)
    assert terminal.status_code == 409
    assert terminal.data["codigo"] == "cita_no_reprogramable"


@pytest.mark.django_db
def test_disponibilidad_no_excluye_cita_de_otro_medico(
    admin_a, suscripcion_amplia, cita_estado, clinica_configurada, medico_citas
):
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="MED-S207-MISMATCH",
        nombre="Médico",
        apellido="Distinto",
        telefono="70000907",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    otro_medico = Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=medico_citas.especialidad,
        numero_colegiatura="COL-S207-MISMATCH",
    )
    respuesta = cliente_autenticado(admin_a).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": otro_medico.pk,
            "fecha": NUEVA_FECHA,
            "cita_id": cita_estado.pk,
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert "cita_id" in respuesta.data["detalles"]


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoCita.CANCELADA, EstadoCita.ATENDIDA, EstadoCita.NO_ASISTIO])
def test_disponibilidad_no_excluye_citas_terminales(
    admin_a, suscripcion_amplia, cita_estado, estado
):
    cita_estado.estado = estado
    cita_estado.save(update_fields=["estado"])
    respuesta = cliente_autenticado(admin_a).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": NUEVA_FECHA,
            "cita_id": cita_estado.pk,
        },
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cita_no_reprogramable"


@pytest.mark.django_db
@pytest.mark.parametrize("cita_id", ["abc", 0, -1])
def test_disponibilidad_rechaza_cita_id_invalido(
    admin_a, suscripcion_amplia, cita_estado, cita_id
):
    respuesta = cliente_autenticado(admin_a).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": NUEVA_FECHA,
            "cita_id": cita_id,
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert "cita_id" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_disponibilidad_oculta_cita_inexistente(
    admin_a, suscripcion_amplia, cita_estado
):
    respuesta = cliente_autenticado(admin_a).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": cita_estado.paciente_id,
            "medico_id": cita_estado.medico_id,
            "fecha": NUEVA_FECHA,
            "cita_id": 999999,
        },
    )
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
def test_disponibilidad_oculta_cita_de_otra_clinica(
    admin_b, suscripcion_b, cita_estado, clinica_b
):
    especialidad = Especialidad.all_objects.filter(clinica=clinica_b).first()
    personal = Personal.all_objects.create(
        clinica=clinica_b,
        ci="MED-B-S207",
        nombre="Médico",
        apellido="Clínica B",
        telefono="70000908",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    medico = Medico.all_objects.create(
        clinica=clinica_b,
        personal=personal,
        especialidad=especialidad,
        numero_colegiatura="COL-B-S207",
    )
    paciente = Paciente.all_objects.create(
        clinica=clinica_b,
        ci="PAC-B-S207",
        nombre="Paciente",
        apellido="Clínica B",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000909",
    )
    respuesta = cliente_autenticado(admin_b).get(
        f"{URL}disponibilidad/",
        {
            "paciente_id": paciente.pk,
            "medico_id": medico.pk,
            "fecha": NUEVA_FECHA,
            "cita_id": cita_estado.pk,
        },
    )
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
@pytest.mark.parametrize("usuario_fixture", ["medico_a", "usuario_paciente_a", "conductor_a"])
@pytest.mark.parametrize("nombre", ["confirmar", "cancelar", "reprogramar"])
def test_roles_no_autorizados_en_acciones(
    request, usuario_fixture, nombre, suscripcion_amplia, cita_estado
):
    usuario = request.getfixturevalue(usuario_fixture)
    datos = {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA} if nombre == "reprogramar" else {}
    respuesta = cliente_autenticado(usuario).post(
        accion(cita_estado, nombre), datos, format="json"
    )
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
@pytest.mark.parametrize("nombre", ["confirmar", "cancelar", "reprogramar"])
def test_acciones_ocultan_cita_de_otra_clinica(
    admin_b, suscripcion_b, nombre, cita_estado
):
    datos = {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA} if nombre == "reprogramar" else {}
    respuesta = cliente_autenticado(admin_b).post(
        accion(cita_estado, nombre), datos, format="json"
    )
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
@pytest.mark.parametrize("nombre", ["confirmar", "cancelar", "reprogramar"])
def test_acciones_requieren_autenticacion(nombre, cliente, cita_estado):
    datos = {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA} if nombre == "reprogramar" else {}
    respuesta = cliente.post(accion(cita_estado, nombre), datos, format="json")
    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


@pytest.mark.django_db
@pytest.mark.parametrize("nombre", ["confirmar", "cancelar", "reprogramar"])
def test_admin_sistema_no_puede_gestionar_citas(
    admin_sistema, nombre, cita_estado
):
    datos = {"fecha": NUEVA_FECHA, "hora": NUEVA_HORA} if nombre == "reprogramar" else {}
    respuesta = cliente_autenticado(admin_sistema).post(
        accion(cita_estado, nombre), datos, format="json"
    )
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("condicion", "codigo"),
    [("clinica", "clinica_inactiva"), ("suscripcion", "suscripcion_vencida")],
)
def test_acciones_exigen_clinica_activa_y_suscripcion(
    admin_a, cita_estado, condicion, codigo, suscripcion_amplia
):
    if condicion == "clinica":
        admin_a.clinica.estado = False
        admin_a.clinica.save(update_fields=["estado"])
    else:
        suscripcion_amplia.estado = "CANCELADA"
        suscripcion_amplia.save(update_fields=["estado"])
    respuesta = cliente_autenticado(admin_a).post(
        accion(cita_estado, "confirmar"), {}, format="json"
    )
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == codigo


@pytest.mark.django_db
def test_integrity_error_inesperado_en_reprogramacion_hace_rollback(
    clinica_configurada, cita_estado
):
    from apps.atencion.services import reprogramar_cita

    fallo = IntegrityError("fallo inesperado")
    with patch.object(Cita, "save", side_effect=fallo):
        with pytest.raises(IntegrityError) as error:
            reprogramar_cita(
                clinica=clinica_configurada,
                cita_id=cita_estado.pk,
                fecha=date(2026, 11, 16),
                hora=time(8, 30),
            )
    assert error.value is fallo
    cita_estado.refresh_from_db()
    assert (cita_estado.fecha, cita_estado.hora, cita_estado.estado) == (
        date(2026, 11, 16), time(8), EstadoCita.PROGRAMADA
    )


@pytest.mark.django_db
def test_openapi_documenta_operaciones_s207():
    respuesta = Client().get("/api/schema/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    esquema = json.loads(respuesta.content)
    rutas = esquema["paths"]
    for nombre in ("confirmar", "cancelar", "reprogramar"):
        ruta = f"/api/v1/citas/{{id}}/{nombre}/"
        assert set(rutas[ruta]) == {"post"}
    disponibilidad = json.dumps(
        rutas["/api/v1/citas/disponibilidad/"]["get"], ensure_ascii=False
    )
    assert "cita_id" in disponibilidad
    documento = json.dumps(esquema, ensure_ascii=False)
    assert "transicion_cita_invalida" in documento
    assert "cita_no_reprogramable" in documento
    assert not any(
        fragmento in ruta
        for ruta in rutas
        for fragmento in ("atender", "no-asistio", "no_asistio")
    )
