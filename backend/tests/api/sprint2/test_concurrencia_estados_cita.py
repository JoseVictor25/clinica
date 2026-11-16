"""Pruebas de concurrencia real de las transiciones de S2-07."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections

from apps.atencion.models import Cita, EstadoCita
from apps.atencion.services import (
    cancelar_cita,
    confirmar_cita,
    crear_cita,
    reprogramar_cita,
)
from apps.core.api_exceptions import Conflicto
from apps.pacientes.models import Paciente
from apps.personal.models import HorarioAtencion, Medico, Personal


FECHA = date(2026, 11, 16)


def paciente_extra(clinica, sufijo):
    return Paciente.all_objects.create(
        clinica=clinica,
        ci=f"PAC-S207-CONC-{sufijo}",
        nombre="Paciente",
        apellido=f"Concurrente {sufijo}",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono=f"70008{sufijo:03d}",
    )


def medico_extra(clinica, medico_base, sufijo):
    personal = Personal.all_objects.create(
        clinica=clinica,
        ci=f"MED-S207-CONC-{sufijo}",
        nombre="Médico",
        apellido=f"Concurrente {sufijo}",
        telefono=f"70009{sufijo:03d}",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    medico = Medico.all_objects.create(
        clinica=clinica,
        personal=personal,
        especialidad=medico_base.especialidad,
        numero_colegiatura=f"COL-S207-CONC-{sufijo}",
    )
    HorarioAtencion.all_objects.create(
        medico=medico,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    return medico


def ejecutar_simultaneo(funcion, barrera):
    close_old_connections()
    try:
        barrera.wait(timeout=5)
        cita = funcion()
        return ("ok", cita.pk)
    except Conflicto as error:
        return ("conflicto", error.codigo)
    finally:
        connections.close_all()


def correr_dos(funciones):
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [
            ejecutor.submit(ejecutar_simultaneo, funcion, barrera)
            for funcion in funciones
        ]
        return [futuro.result(timeout=10) for futuro in futuros]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("servicio", "estado_final"),
    [
        (confirmar_cita, EstadoCita.CONFIRMADA),
        (cancelar_cita, EstadoCita.CANCELADA),
    ],
)
def test_doble_transicion_sobre_misma_cita_es_serializada(
    clinica_configurada, paciente_a, medico_citas, horario_lunes, servicio, estado_final
):
    assert connection.vendor == "postgresql"
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Concurrente",
    )

    resultados = correr_dos([
        lambda: servicio(clinica=clinica_configurada, cita_id=cita.pk),
        lambda: servicio(clinica=clinica_configurada, cita_id=cita.pk),
    ])

    assert sorted(resultado[0] for resultado in resultados) == ["conflicto", "ok"]
    assert ("conflicto", "transicion_cita_invalida") in resultados
    cita.refresh_from_db()
    assert cita.estado == estado_final


@pytest.mark.django_db(transaction=True)
def test_confirmar_y_cancelar_simultaneamente_no_dejan_estado_imposible(
    clinica_configurada, paciente_a, medico_citas, horario_lunes
):
    assert connection.vendor == "postgresql"
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Transiciones simultáneas",
    )

    resultados = correr_dos([
        lambda: confirmar_cita(clinica=clinica_configurada, cita_id=cita.pk),
        lambda: cancelar_cita(clinica=clinica_configurada, cita_id=cita.pk),
    ])

    assert resultados.count(("conflicto", "transicion_cita_invalida")) in (0, 1)
    cita.refresh_from_db()
    assert cita.estado == EstadoCita.CANCELADA


@pytest.mark.django_db(transaction=True)
def test_dos_reprogramaciones_de_misma_cita_quedan_consistentes(
    clinica_configurada, paciente_a, medico_citas, horario_lunes
):
    assert connection.vendor == "postgresql"
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Reprogramaciones simultáneas",
    )

    resultados = correr_dos([
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita.pk, fecha=FECHA, hora=time(8, 30)
        ),
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita.pk, fecha=FECHA, hora=time(9)
        ),
    ])

    assert all(resultado[0] == "ok" for resultado in resultados)
    cita.refresh_from_db()
    assert cita.estado == EstadoCita.PROGRAMADA
    assert cita.hora in (time(8, 30), time(9))
    assert Cita.all_objects.filter(pk=cita.pk).count() == 1


@pytest.mark.django_db(transaction=True)
def test_reprogramaciones_no_reservan_mismo_medico_y_horario(
    clinica_configurada, paciente_a, medico_citas, horario_lunes
):
    assert connection.vendor == "postgresql"
    otro_paciente = paciente_extra(clinica_configurada, 1)
    cita_a = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Primera",
    )
    cita_b = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=otro_paciente,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(9),
        motivo="Segunda",
    )

    resultados = correr_dos([
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita_a.pk, fecha=FECHA, hora=time(8, 30)
        ),
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita_b.pk, fecha=FECHA, hora=time(8, 30)
        ),
    ])

    assert sorted(resultado[0] for resultado in resultados) == ["conflicto", "ok"]
    assert ("conflicto", "horario_no_disponible") in resultados
    assert Cita.all_objects.filter(fecha=FECHA, hora=time(8, 30)).count() == 1


@pytest.mark.django_db(transaction=True)
def test_reprogramaciones_no_reservan_mismo_paciente_y_horario(
    clinica_configurada, paciente_a, medico_citas, horario_lunes
):
    assert connection.vendor == "postgresql"
    otro_medico = medico_extra(clinica_configurada, medico_citas, 2)
    cita_a = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Primera",
    )
    cita_b = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=otro_medico,
        fecha=FECHA,
        hora=time(9),
        motivo="Segunda",
    )

    resultados = correr_dos([
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita_a.pk, fecha=FECHA, hora=time(8, 30)
        ),
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita_b.pk, fecha=FECHA, hora=time(8, 30)
        ),
    ])

    assert sorted(resultado[0] for resultado in resultados) == ["conflicto", "ok"]
    assert ("conflicto", "paciente_no_disponible") in resultados
    assert Cita.all_objects.filter(paciente=paciente_a, fecha=FECHA, hora=time(8, 30)).count() == 1


@pytest.mark.django_db(transaction=True)
def test_creacion_y_reprogramacion_no_reservan_mismo_medico_y_horario(
    clinica_configurada, paciente_a, medico_citas, horario_lunes
):
    assert connection.vendor == "postgresql"
    otro_paciente = paciente_extra(clinica_configurada, 3)
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        motivo="Se reprograma",
    )
    datos_creacion = {
        "paciente_id": otro_paciente.pk,
        "medico_id": medico_citas.pk,
        "fecha": FECHA,
        "hora": time(8, 30),
        "motivo": "Se crea",
    }

    resultados = correr_dos([
        lambda: reprogramar_cita(
            clinica=clinica_configurada, cita_id=cita.pk, fecha=FECHA, hora=time(8, 30)
        ),
        lambda: crear_cita(clinica_configurada, datos_creacion),
    ])

    assert sorted(resultado[0] for resultado in resultados) == ["conflicto", "ok"]
    assert ("conflicto", "horario_no_disponible") in resultados
    assert Cita.all_objects.filter(fecha=FECHA, hora=time(8, 30)).count() == 1
