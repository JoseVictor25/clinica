"""Pruebas API de telemedicina (modalidad virtual, Daily.co y sala virtual)."""

from datetime import date, time
import json
from unittest.mock import patch

import pytest

from apps.atencion.models import Cita, EstadoCita, ModalidadCita
from apps.core.seed_data import ROL_MEDICO
from apps.personal.models import HorarioAtencion
from tests.api.helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)


FECHA = date(2026, 11, 16)


class _RespuestaDailyMock:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.django_db
def test_crear_cita_presencial_deja_link_null(
    recepcionista_a, suscripcion_amplia, clinica_configurada, paciente_a, medico_citas
):
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=FECHA.weekday(),
        hora_inicio=time(8, 0),
        hora_fin=time(10, 0),
    )

    respuesta = cliente_autenticado(recepcionista_a).post(
        "/api/v1/citas/",
        {
            "paciente_id": paciente_a.pk,
            "medico_id": medico_citas.pk,
            "fecha": FECHA.isoformat(),
            "hora": "08:00",
            "modalidad": ModalidadCita.PRESENCIAL,
            "motivo": "Control presencial",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["modalidad"] == ModalidadCita.PRESENCIAL
    assert respuesta.data["link_videollamada"] is None


@pytest.mark.django_db
def test_crear_cita_virtual_genera_link_daily(
    recepcionista_a, suscripcion_amplia, clinica_configurada, paciente_a, medico_citas, settings
):
    settings.DAILY_API_KEY = "test-daily-key"
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=FECHA.weekday(),
        hora_inicio=time(8, 0),
        hora_fin=time(10, 0),
    )

    with patch(
        "apps.atencion.services.urllib_request.urlopen",
        return_value=_RespuestaDailyMock({"url": "https://clinicasaas.daily.co/sala-test-1"}),
    ) as mock_urlopen:
        respuesta = cliente_autenticado(recepcionista_a).post(
            "/api/v1/citas/",
            {
                "paciente_id": paciente_a.pk,
                "medico_id": medico_citas.pk,
                "fecha": FECHA.isoformat(),
                "hora": "08:30",
                "modalidad": ModalidadCita.VIRTUAL,
                "motivo": "Teleconsulta",
            },
            format="json",
        )

    assert respuesta.status_code == 201
    assert mock_urlopen.call_count == 1
    assert respuesta.data["modalidad"] == ModalidadCita.VIRTUAL
    assert respuesta.data["link_videollamada"] == "https://clinicasaas.daily.co/sala-test-1"


@pytest.mark.django_db
def test_sala_virtual_accesible_para_medico_y_paciente_asignados(
    clinica_configurada, suscripcion_amplia, medico_a, usuario_paciente_a, paciente_a
):
    _, medico = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="CI-TM-001",
        colegiatura="COL-TM-001",
    )
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])

    cita_virtual = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(9, 0),
        estado=EstadoCita.CONFIRMADA,
        modalidad=ModalidadCita.VIRTUAL,
        link_videollamada="https://clinicasaas.daily.co/sala-tm-1",
        motivo="Control virtual",
    )
    cita_presencial = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(9, 30),
        estado=EstadoCita.CONFIRMADA,
        modalidad=ModalidadCita.PRESENCIAL,
        link_videollamada=None,
        motivo="Control presencial",
    )

    resp_medico = cliente_autenticado(medico_a).get(f"/api/v1/citas/{cita_virtual.pk}/sala-virtual/")
    assert resp_medico.status_code == 200
    assert resp_medico.data["link_videollamada"] == "https://clinicasaas.daily.co/sala-tm-1"

    resp_paciente = cliente_autenticado(usuario_paciente_a).get(
        f"/api/v1/citas/{cita_virtual.pk}/sala-virtual/"
    )
    assert resp_paciente.status_code == 200
    assert resp_paciente.data["link_videollamada"] == "https://clinicasaas.daily.co/sala-tm-1"

    resp_presencial = cliente_autenticado(medico_a).get(
        f"/api/v1/citas/{cita_presencial.pk}/sala-virtual/"
    )
    assert resp_presencial.status_code == 409

    otro_medico_user = crear_usuario_con_rol(clinica_configurada, "otro_med_tm", ROL_MEDICO)
    crear_personal_medico(
        clinica_configurada,
        otro_medico_user,
        ci="CI-TM-002",
        colegiatura="COL-TM-002",
    )
    resp_ajeno = cliente_autenticado(otro_medico_user).get(
        f"/api/v1/citas/{cita_virtual.pk}/sala-virtual/"
    )
    assert resp_ajeno.status_code == 404
