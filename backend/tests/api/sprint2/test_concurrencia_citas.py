"""Pruebas de concurrencia real de S2-06 sobre PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections

from apps.atencion.models import Cita
from apps.atencion.services import crear_cita
from apps.core.api_exceptions import Conflicto
from apps.pacientes.models import Paciente
from apps.personal.models import HorarioAtencion, Medico, Personal


FECHA = date(2026, 11, 16)


def datos(paciente, medico):
    return {
        "paciente_id": paciente.pk,
        "medico_id": medico.pk,
        "fecha": FECHA,
        "hora": time(8),
        "motivo": "Prueba concurrente",
    }


def ejecutar_en_conexion_independiente(clinica, entrada, barrera):
    close_old_connections()
    try:
        barrera.wait(timeout=5)
        cita = crear_cita(clinica, entrada)
        return ("creada", cita.pk)
    except Conflicto as error:
        return ("conflicto", error.codigo)
    finally:
        connections.close_all()


def segundo_paciente(clinica):
    return Paciente.all_objects.create(
        clinica=clinica,
        ci="PAC-CONC-002",
        nombre="Paciente",
        apellido="Concurrente",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000702",
    )


def segundo_medico(clinica, medico_base):
    personal = Personal.all_objects.create(
        clinica=clinica,
        ci="MED-CONC-002",
        nombre="Médico",
        apellido="Concurrente",
        telefono="70000703",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    medico = Medico.all_objects.create(
        clinica=clinica,
        personal=personal,
        especialidad=medico_base.especialidad,
        numero_colegiatura="COL-CONC-002",
    )
    HorarioAtencion.all_objects.create(
        medico=medico,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    return medico


@pytest.mark.django_db(transaction=True)
def test_dos_solicitudes_no_reservan_el_mismo_medico(
    clinica_configurada, paciente_a, medico_citas
):
    assert connection.vendor == "postgresql"
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    paciente_b = segundo_paciente(clinica_configurada)
    entradas = [datos(paciente_a, medico_citas), datos(paciente_b, medico_citas)]
    barrera = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(
            ejecutor.map(
                lambda entrada: ejecutar_en_conexion_independiente(
                    clinica_configurada, entrada, barrera
                ),
                entradas,
            )
        )

    assert sorted(resultado[0] for resultado in resultados) == [
        "conflicto",
        "creada",
    ]
    assert ("conflicto", "horario_no_disponible") in resultados
    assert Cita.all_objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_dos_solicitudes_no_reservan_al_mismo_paciente(
    clinica_configurada, paciente_a, medico_citas
):
    assert connection.vendor == "postgresql"
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    medico_b = segundo_medico(clinica_configurada, medico_citas)
    entradas = [datos(paciente_a, medico_citas), datos(paciente_a, medico_b)]
    barrera = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(
            ejecutor.map(
                lambda entrada: ejecutar_en_conexion_independiente(
                    clinica_configurada, entrada, barrera
                ),
                entradas,
            )
        )

    assert sorted(resultado[0] for resultado in resultados) == [
        "conflicto",
        "creada",
    ]
    assert ("conflicto", "paciente_no_disponible") in resultados
    assert Cita.all_objects.count() == 1
