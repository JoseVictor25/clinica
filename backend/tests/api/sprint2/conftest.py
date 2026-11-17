import pytest
from datetime import date, datetime, time

from django.utils import timezone

from apps.core.seed_data import ROL_CONDUCTOR, ROL_PACIENTE, ROL_RECEPCIONISTA
from apps.pacientes.models import Paciente
from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from tests.api.helpers import crear_usuario_con_rol


@pytest.fixture(autouse=True)
def momento_determinista_sprint2(monkeypatch):
    """Evita que las pruebas de citas dependan del reloj de la máquina."""

    momento = timezone.make_aware(
        datetime(2026, 11, 16, 7, 0),
        timezone.get_current_timezone(),
    )
    monkeypatch.setattr("apps.atencion.services._momento_local", lambda: momento)


@pytest.fixture
def recepcionista_a(clinica_configurada):
    return crear_usuario_con_rol(clinica_configurada, "recepcion_a", ROL_RECEPCIONISTA)


@pytest.fixture
def conductor_a(clinica_configurada):
    return crear_usuario_con_rol(clinica_configurada, "conductor_a", ROL_CONDUCTOR)


@pytest.fixture
def usuario_paciente_a(clinica_configurada):
    return crear_usuario_con_rol(clinica_configurada, "paciente_a", ROL_PACIENTE)


@pytest.fixture
def datos_paciente():
    return {"ci": "PAC-001", "nombre": "Ana", "apellido": "Pérez", "sexo": "F", "fecha_nacimiento": "1990-05-10", "telefono": "70000001", "email": "ana@example.com", "estado": True}


@pytest.fixture
def paciente_a(clinica_configurada, datos_paciente):
    return Paciente.all_objects.create(clinica=clinica_configurada, **datos_paciente)


@pytest.fixture
def especialidad_citas(clinica_configurada):
    return Especialidad.all_objects.filter(clinica=clinica_configurada).first()


@pytest.fixture
def medico_citas(clinica_configurada, especialidad_citas):
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="MED-CITAS-001",
        nombre="Mario",
        apellido="Médico",
        telefono="70000100",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
        estado=True,
    )
    return Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=especialidad_citas,
        numero_colegiatura="COL-CITAS-001",
        estado=True,
    )


@pytest.fixture
def horario_lunes(medico_citas):
    return HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8, 0),
        hora_fin=time(10, 0),
    )
