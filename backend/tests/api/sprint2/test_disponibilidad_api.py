"""Pruebas API del cálculo básico de disponibilidad de S2-05."""
from datetime import date, time

import pytest

from apps.atencion.models import Cita, EstadoCita
from apps.pacientes.models import Paciente
from apps.personal.models import HorarioAtencion
from tests.api.helpers import cliente_autenticado

URL = "/api/v1/citas/disponibilidad/"
FECHA_LUNES = date(2026, 11, 16)


def parametros(paciente, medico, **cambios):
    datos = {
        "paciente_id": paciente.pk,
        "medico_id": medico.pk,
        "fecha": FECHA_LUNES.isoformat(),
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
@pytest.mark.parametrize("usuario_fixture", ["admin_a", "recepcionista_a"])
def test_genera_bloques_ordenados_de_30_minutos(
    request,
    usuario_fixture,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
    horario_lunes,
):
    usuario = request.getfixturevalue(usuario_fixture)
    respuesta = cliente_autenticado(usuario).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert respuesta.status_code == 200
    assert respuesta.data == {
        "paciente_id": paciente_a.pk,
        "medico_id": medico_citas.pk,
        "fecha": "2026-11-16",
        "duracion_minutos": 30,
        "horarios": ["08:00", "08:30", "09:00", "09:30"],
    }
    assert Cita.all_objects.count() == 0


@pytest.mark.django_db
def test_no_genera_bloque_que_supera_hora_fin(
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(9, 10),
    )
    respuesta = cliente_autenticado(admin_a).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert respuesta.data["horarios"] == ["08:00", "08:30"]


@pytest.mark.django_db
def test_elimina_duplicados_de_horarios_superpuestos(
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(9),
    )
    HorarioAtencion.all_objects.create(
        medico=medico_citas,
        dia_semana=0,
        hora_inicio=time(8, 30),
        hora_fin=time(9, 30),
    )
    respuesta = cliente_autenticado(admin_a).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert respuesta.data["horarios"] == ["08:00", "08:30", "09:00"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado,bloquea",
    [
        (EstadoCita.PROGRAMADA, True),
        (EstadoCita.CONFIRMADA, True),
        (EstadoCita.ATENDIDA, True),
        (EstadoCita.CANCELADA, False),
        (EstadoCita.NO_ASISTIO, False),
    ],
)
def test_estados_que_bloquean_disponibilidad(
    estado,
    bloquea,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
    horario_lunes,
    clinica_configurada,
):
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA_LUNES,
        hora=time(8),
        estado=estado,
        motivo="Control",
    )
    respuesta = cliente_autenticado(admin_a).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert ("08:00" not in respuesta.data["horarios"]) is bloquea


@pytest.mark.django_db
def test_cita_del_paciente_con_otro_medico_excluye_hora(
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
    horario_lunes,
    clinica_configurada,
):
    from apps.personal.models import Medico, Personal

    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="MED-DISP-2",
        nombre="Otro",
        apellido="Médico",
        telefono="70000400",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    otro = Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=medico_citas.especialidad,
        numero_colegiatura="COL-DISP-2",
    )
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=otro,
        fecha=FECHA_LUNES,
        hora=time(8, 30),
        motivo="Otra",
    )
    respuesta = cliente_autenticado(admin_a).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert "08:30" not in respuesta.data["horarios"]


@pytest.mark.django_db
def test_sin_horario_devuelve_lista_vacia(
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    respuesta = cliente_autenticado(admin_a).get(
        URL, parametros(paciente_a, medico_citas)
    )
    assert respuesta.status_code == 200
    assert respuesta.data["horarios"] == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cambios,campo",
    [
        ({"paciente_id": None}, "paciente_id"),
        ({"paciente_id": "abc"}, "paciente_id"),
        ({"medico_id": None}, "medico_id"),
        ({"medico_id": "abc"}, "medico_id"),
        ({"fecha": None}, "fecha"),
        ({"fecha": "16/11/2026"}, "fecha"),
    ],
)
def test_parametros_invalidos(
    cambios,
    campo,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    datos = parametros(paciente_a, medico_citas)
    if cambios[campo] is None:
        datos.pop(campo)
    else:
        datos.update(cambios)
    respuesta = cliente_autenticado(admin_a).get(URL, datos)
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
def test_recursos_ajenos_o_inexistentes_no_se_revelan(
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    cliente = cliente_autenticado(admin_a)
    paciente = cliente.get(
        URL, parametros(paciente_a, medico_citas, paciente_id=999999)
    )
    medico = cliente.get(
        URL, parametros(paciente_a, medico_citas, medico_id=999999)
    )
    assert paciente.status_code == 404
    assert medico.status_code == 404
    assert paciente.data["codigo"] == "no_encontrado"
    assert medico.data["codigo"] == "no_encontrado"

