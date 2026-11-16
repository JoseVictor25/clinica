"""Pruebas API de las reglas de negocio de S2-06."""

from datetime import date, datetime, time

import pytest
from django.utils import timezone

from apps.atencion.models import Cita, EstadoCita
from apps.personal.models import DiaSemana, HorarioAtencion, Medico, Personal
from tests.api.helpers import cliente_autenticado


URL = "/api/v1/citas/"
DISPONIBILIDAD = f"{URL}disponibilidad/"
FECHA = date(2026, 11, 16)


def horario(medico, inicio=time(8), fin=time(10), dia=DiaSemana.LUNES):
    return HorarioAtencion.all_objects.create(
        medico=medico,
        dia_semana=dia,
        hora_inicio=inicio,
        hora_fin=fin,
    )


def entrada(paciente, medico, fecha=FECHA, hora_cita=time(8)):
    return {
        "paciente_id": paciente.pk,
        "medico_id": medico.pk,
        "fecha": fecha.isoformat(),
        "hora": hora_cita.strftime("%H:%M"),
        "motivo": "Control",
    }


def fijar_ahora(monkeypatch, valor):
    consciente = timezone.make_aware(valor, timezone.get_current_timezone())
    monkeypatch.setattr("apps.atencion.services._momento_local", lambda: consciente)


@pytest.mark.django_db
def test_rechaza_fecha_pasada(
    admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas)
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        entrada(paciente_a, medico_citas, date(2026, 11, 15)),
        format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "fecha_cita_pasada"
    assert "fecha" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_rechaza_hora_pasada_del_dia_actual(
    monkeypatch, admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, time(6), time(9))
    fijar_ahora(monkeypatch, datetime(2026, 11, 16, 7, 1))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=time(7)), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "hora_cita_pasada"
    assert "hora" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_permite_el_instante_actual_exacto(
    monkeypatch, admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, time(7), time(9))
    fijar_ahora(monkeypatch, datetime(2026, 11, 16, 7, 0))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=time(7)), format="json"
    )
    assert respuesta.status_code == 201


@pytest.mark.django_db
def test_rechaza_bloque_si_ya_transcurrieron_segundos(
    monkeypatch, admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, time(7), time(9))
    fijar_ahora(monkeypatch, datetime(2026, 11, 16, 7, 0, 1))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=time(7)), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "hora_cita_pasada"


@pytest.mark.django_db
def test_acepta_bloque_que_termina_exactamente_en_hora_fin(
    admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, time(8), time(9, 30))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=time(9)), format="json"
    )
    assert respuesta.status_code == 201


@pytest.mark.django_db
def test_acepta_fecha_futura_con_horario_valido(
    admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, dia=DiaSemana.MARTES)
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        entrada(paciente_a, medico_citas, fecha=date(2026, 11, 17)),
        format="json",
    )
    assert respuesta.status_code == 201


@pytest.mark.django_db
def test_rechaza_creacion_sin_horario(
    admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "fuera_horario"


@pytest.mark.django_db
@pytest.mark.parametrize("hora_cita", [time(7, 30), time(8, 15), time(10)])
def test_rechaza_bloques_fuera_del_horario(
    hora_cita,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    horario(medico_citas, time(8), time(10))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=hora_cita), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "fuera_horario"
    assert "hora" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_no_acepta_bloque_en_pausa_entre_horarios(
    admin_a, suscripcion_amplia, paciente_a, medico_citas
):
    horario(medico_citas, time(8), time(9))
    horario(medico_citas, time(10), time(11))
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas, hora_cita=time(9)), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "fuera_horario"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("recurso", "codigo"),
    [
        ("paciente", "paciente_inactivo"),
        ("medico", "medico_inactivo"),
        ("personal", "medico_inactivo"),
    ],
)
def test_rechaza_recursos_inactivos(
    recurso,
    codigo,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    horario(medico_citas)
    objeto = {
        "paciente": paciente_a,
        "medico": medico_citas,
        "personal": medico_citas.personal,
    }[recurso]
    objeto.estado = False
    objeto.save(update_fields=["estado"])
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == codigo


@pytest.mark.django_db
def test_detecta_solapamiento_general_y_permite_contiguidad(
    admin_a,
    suscripcion_amplia,
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    horario(medico_citas)
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8, 15),
        motivo="Registro legado solapado",
    )
    otro_paciente = type(paciente_a).all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-S206-002",
        nombre="Otra",
        apellido="Persona",
        sexo="F",
        fecha_nacimiento=date(1995, 1, 1),
        telefono="70000602",
    )
    cliente = cliente_autenticado(admin_a)
    solapada = cliente.post(
        URL, entrada(otro_paciente, medico_citas, hora_cita=time(8)), format="json"
    )
    contigua = cliente.post(
        URL, entrada(otro_paciente, medico_citas, hora_cita=time(9)), format="json"
    )
    assert solapada.status_code == 409
    assert solapada.data["codigo"] == "horario_no_disponible"
    assert contigua.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize("recurso", ["medico", "paciente"])
@pytest.mark.parametrize("hora_nueva", [time(8), time(8, 30)])
def test_detecta_solapamientos_parciales_de_medico_y_paciente(
    recurso,
    hora_nueva,
    admin_a,
    suscripcion_amplia,
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    horario(medico_citas)
    otro_paciente = type(paciente_a).all_objects.create(
        clinica=clinica_configurada,
        ci=f"PAC-SOL-{recurso}-{hora_nueva.minute}",
        nombre="Otra",
        apellido="Persona",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000604",
    )
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci=f"MED-SOL-{recurso}-{hora_nueva.minute}",
        nombre="Otro",
        apellido="Médico",
        telefono="70000605",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    otro_medico = Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=medico_citas.especialidad,
        numero_colegiatura=f"COL-SOL-{recurso}-{hora_nueva.minute}",
    )
    horario(otro_medico)
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8, 15),
        motivo="Existente no alineada",
    )
    paciente_nuevo = otro_paciente if recurso == "medico" else paciente_a
    medico_nuevo = medico_citas if recurso == "medico" else otro_medico
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        entrada(paciente_nuevo, medico_nuevo, hora_cita=hora_nueva),
        format="json",
    )
    assert respuesta.status_code == 409
    esperado = (
        "horario_no_disponible"
        if recurso == "medico"
        else "paciente_no_disponible"
    )
    assert respuesta.data["codigo"] == esperado


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO])
def test_estados_finales_no_bloquean(
    estado,
    admin_a,
    suscripcion_amplia,
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    horario(medico_citas)
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(8),
        estado=estado,
        motivo="Finalizada",
    )
    respuesta = cliente_autenticado(admin_a).post(
        URL, entrada(paciente_a, medico_citas), format="json"
    )
    assert respuesta.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("fecha", "dia"),
    [
        (date(2026, 11, 16), DiaSemana.LUNES),
        (date(2026, 11, 17), DiaSemana.MARTES),
        (date(2026, 11, 18), DiaSemana.MIERCOLES),
        (date(2026, 11, 19), DiaSemana.JUEVES),
        (date(2026, 11, 20), DiaSemana.VIERNES),
        (date(2026, 11, 21), DiaSemana.SABADO),
        (date(2026, 11, 22), DiaSemana.DOMINGO),
    ],
)
def test_mapeo_explicito_de_dias(
    fecha,
    dia,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    horario(medico_citas, dia=dia)
    respuesta = cliente_autenticado(admin_a).get(
        DISPONIBILIDAD,
        {
            "paciente_id": paciente_a.pk,
            "medico_id": medico_citas.pk,
            "fecha": fecha.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.data["horarios"][0] == "08:00"


@pytest.mark.django_db
def test_disponibilidad_excluye_bloques_pasados_y_solapados(
    monkeypatch,
    admin_a,
    suscripcion_amplia,
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    horario(medico_citas, time(7), time(10))
    fijar_ahora(monkeypatch, datetime(2026, 11, 16, 8, 1))
    Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=FECHA,
        hora=time(9),
        motivo="Ocupada",
    )
    respuesta = cliente_autenticado(admin_a).get(
        DISPONIBILIDAD,
        {
            "paciente_id": paciente_a.pk,
            "medico_id": medico_citas.pk,
            "fecha": FECHA.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.data["horarios"] == ["08:30", "09:30"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("recurso", "codigo", "estado_http"),
    [
        ("fecha", "fecha_cita_pasada", 400),
        ("paciente", "paciente_inactivo", 409),
        ("medico", "medico_inactivo", 409),
        ("personal", "medico_inactivo", 409),
    ],
)
def test_disponibilidad_rechaza_causas_invalidas(
    recurso,
    codigo,
    estado_http,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    horario(medico_citas)
    fecha = FECHA
    if recurso == "fecha":
        fecha = date(2026, 11, 15)
    else:
        objeto = {
            "paciente": paciente_a,
            "medico": medico_citas,
            "personal": medico_citas.personal,
        }[recurso]
        objeto.estado = False
        objeto.save(update_fields=["estado"])
    respuesta = cliente_autenticado(admin_a).get(
        DISPONIBILIDAD,
        {
            "paciente_id": paciente_a.pk,
            "medico_id": medico_citas.pk,
            "fecha": fecha.isoformat(),
        },
    )
    assert respuesta.status_code == estado_http
    assert respuesta.data["codigo"] == codigo
    assert not Cita.all_objects.exists()


@pytest.mark.django_db
def test_disponibilidad_futura_totalmente_ocupada_devuelve_lista_vacia(
    admin_a,
    suscripcion_amplia,
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    fecha = date(2026, 11, 17)
    horario(medico_citas, time(8), time(9), DiaSemana.MARTES)
    otro_paciente = type(paciente_a).all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-S206-003",
        nombre="Ocupante",
        apellido="Agenda",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000603",
    )
    for hora_cita in (time(8), time(8, 30)):
        Cita.all_objects.create(
            clinica=clinica_configurada,
            paciente=otro_paciente,
            medico=medico_citas,
            fecha=fecha,
            hora=hora_cita,
            motivo="Ocupada",
        )
    respuesta = cliente_autenticado(admin_a).get(
        DISPONIBILIDAD,
        {
            "paciente_id": paciente_a.pk,
            "medico_id": medico_citas.pk,
            "fecha": fecha.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.data["duracion_minutos"] == 30
    assert respuesta.data["horarios"] == []
    assert Cita.all_objects.count() == 2
