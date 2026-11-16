"""Pruebas API de S2-05: listado, detalle y creación de citas."""
from datetime import date, time
import json
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.test import Client

from apps.atencion.models import Cita, EstadoCita
from apps.atencion.services import crear_cita
from apps.core.api_exceptions import Conflicto
from apps.pacientes.models import Paciente
from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from tests.api.helpers import cliente_autenticado


URL = "/api/v1/citas/"


@pytest.fixture(autouse=True)
def horario_base_para_pruebas_de_creacion(request):
    if "medico_citas" in request.fixturenames:
        request.getfixturevalue("horario_lunes")


def entrada_cita(paciente, medico, **cambios):
    datos = {
        "paciente_id": paciente.pk,
        "medico_id": medico.pk,
        "fecha": "2026-11-16",
        "hora": "08:00",
        "motivo": "Control general",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def cita_a(clinica_configurada, paciente_a, medico_citas):
    return Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_citas,
        fecha=date(2026, 11, 16),
        hora=time(8, 0),
        motivo="Control general",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("usuario_fixture", ["admin_a", "recepcionista_a"])
def test_roles_autorizados_listan_crean_y_consultan(
    request,
    usuario_fixture,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    usuario = request.getfixturevalue(usuario_fixture)
    cliente = cliente_autenticado(usuario)
    creada = cliente.post(URL, entrada_cita(paciente_a, medico_citas), format="json")

    assert creada.status_code == 201
    assert creada.data["estado"] == EstadoCita.PROGRAMADA
    assert creada.data["paciente_id"] == paciente_a.pk
    assert creada.data["medico_id"] == medico_citas.pk
    assert creada.data["especialidad_nombre"] == medico_citas.especialidad.nombre
    cita = Cita.all_objects.get(pk=creada.data["id"])
    assert cita.clinica_id == usuario.clinica_id
    assert cita.motivo == "Control general"

    lista = cliente.get(URL)
    detalle = cliente.get(f"{URL}{cita.pk}/")
    assert lista.status_code == 200
    assert lista.data["count"] == 1
    assert detalle.status_code == 200
    assert detalle.data["id"] == cita.pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    "campo",
    [
        "clinica",
        "clinica_id",
        "estado",
        "especialidad",
        "especialidad_id",
        "duracion",
        "hora_fin",
    ],
)
def test_campos_prohibidos_se_rechazan(
    campo,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    datos = entrada_cita(paciente_a, medico_citas)
    datos[campo] = 1
    respuesta = cliente_autenticado(admin_a).post(URL, datos, format="json")

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]
    assert not Cita.all_objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"paciente_id": None}, "paciente_id"),
        ({"paciente_id": "abc"}, "paciente_id"),
        ({"medico_id": None}, "medico_id"),
        ({"medico_id": "abc"}, "medico_id"),
        ({"fecha": None}, "fecha"),
        ({"fecha": "16/11/2026"}, "fecha"),
        ({"hora": None}, "hora"),
        ({"hora": "25:00"}, "hora"),
        ({"motivo": None}, "motivo"),
        ({"motivo": ""}, "motivo"),
        ({"motivo": "   "}, "motivo"),
        ({"motivo": "x" * 256}, "motivo"),
    ],
)
def test_entrada_invalida_devuelve_detalles_y_no_crea(
    cambio,
    campo,
    admin_a,
    suscripcion_amplia,
    paciente_a,
    medico_citas,
):
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        entrada_cita(paciente_a, medico_citas, **cambio),
        format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]
    assert not Cita.all_objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["paciente_id", "medico_id", "fecha", "hora", "motivo"])
def test_campos_obligatorios(campo, admin_a, suscripcion_amplia, paciente_a, medico_citas):
    datos = entrada_cita(paciente_a, medico_citas)
    datos.pop(campo)
    respuesta = cliente_autenticado(admin_a).post(URL, datos, format="json")
    assert respuesta.status_code == 400
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
def test_conflictos_exactos_de_medico_y_paciente(
    admin_a,
    suscripcion_amplia,
    cita_a,
    clinica_configurada,
    medico_citas,
):
    otro_paciente = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-CITA-002",
        nombre="Otro",
        apellido="Paciente",
        sexo="M",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000200",
    )
    cliente = cliente_autenticado(admin_a)
    medico_ocupado = cliente.post(
        URL, entrada_cita(otro_paciente, medico_citas), format="json"
    )
    assert medico_ocupado.status_code == 409
    assert medico_ocupado.data["codigo"] == "horario_no_disponible"

    especialidad = medico_citas.especialidad
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="MED-CITAS-002",
        nombre="Otra",
        apellido="Doctora",
        telefono="70000201",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    otro_medico = Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=especialidad,
        numero_colegiatura="COL-CITAS-002",
    )
    HorarioAtencion.all_objects.create(
        medico=otro_medico,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    paciente_ocupado = cliente.post(
        URL, entrada_cita(cita_a.paciente, otro_medico), format="json"
    )
    assert paciente_ocupado.status_code == 409
    assert paciente_ocupado.data["codigo"] == "paciente_no_disponible"


@pytest.mark.django_db
def test_recursos_ajenos_son_tenant_safe(
    admin_a,
    suscripcion_amplia,
    clinica_b,
    paciente_a,
    medico_citas,
):
    especialidad_b = Especialidad.all_objects.create(
        clinica=clinica_b, nombre="Especialidad B"
    )
    personal_b = Personal.all_objects.create(
        clinica=clinica_b,
        ci="MED-B-CITA",
        nombre="Médico",
        apellido="B",
        telefono="70000300",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    medico_b = Medico.all_objects.create(
        clinica=clinica_b,
        personal=personal_b,
        especialidad=especialidad_b,
        numero_colegiatura="COL-B-CITA",
    )
    paciente_b = Paciente.all_objects.create(
        clinica=clinica_b,
        ci="PAC-B-CITA",
        nombre="Paciente",
        apellido="B",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000301",
    )
    cita_b = Cita.all_objects.create(
        clinica=clinica_b,
        paciente=paciente_b,
        medico=medico_b,
        fecha=date(2026, 11, 16),
        hora=time(8),
        motivo="Ajena",
    )
    cliente = cliente_autenticado(admin_a)

    assert cliente.get(f"{URL}{cita_b.pk}/").status_code == 404
    paciente_ajeno = cliente.post(
        URL, entrada_cita(paciente_b, medico_citas), format="json"
    )
    medico_ajeno = cliente.post(
        URL, entrada_cita(paciente_a, medico_b), format="json"
    )
    assert paciente_ajeno.status_code == 404
    assert medico_ajeno.status_code == 404
    assert paciente_ajeno.data["codigo"] == "no_encontrado"
    assert medico_ajeno.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "usuario_fixture",
    ["medico_a", "usuario_paciente_a", "conductor_a"],
)
def test_roles_no_autorizados(usuario_fixture, request, suscripcion_amplia):
    usuario = request.getfixturevalue(usuario_fixture)
    respuesta = cliente_autenticado(usuario).get(URL)
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_admin_sistema_anonimo_y_suscripcion_vencida(
    admin_sistema,
    admin_a,
    cliente,
):
    assert cliente_autenticado(admin_sistema).get(URL).status_code == 403
    anonima = cliente.get(URL)
    vencida = cliente_autenticado(admin_a).get(URL)
    assert anonima.status_code == 401
    assert anonima.data["codigo"] == "no_autenticado"
    assert vencida.status_code == 403
    assert vencida.data["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_listado_filtros_orden_y_paginacion(
    admin_a,
    suscripcion_amplia,
    cita_a,
):
    cliente = cliente_autenticado(admin_a)
    por_fecha = cliente.get(URL, {"fecha": "2026-11-16"})
    por_paciente = cliente.get(URL, {"paciente_id": cita_a.paciente_id})
    por_medico = cliente.get(URL, {"medico_id": cita_a.medico_id})
    por_estado = cliente.get(URL, {"estado": EstadoCita.PROGRAMADA})
    for respuesta in (por_fecha, por_paciente, por_medico, por_estado):
        assert respuesta.status_code == 200
        assert respuesta.data["count"] == 1
        assert {"count", "next", "previous", "results"} <= set(respuesta.data)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "parametros",
    [
        {"fecha": "16/11/2026"},
        {"paciente_id": "abc"},
        {"medico_id": "abc"},
        {"estado": "INVALIDO"},
    ],
)
def test_filtros_invalidos(parametros, admin_a, suscripcion_amplia):
    respuesta = cliente_autenticado(admin_a).get(URL, parametros)
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["patch", "put", "delete"])
def test_metodos_de_edicion_no_permitidos(
    metodo,
    admin_a,
    suscripcion_amplia,
    cita_a,
):
    respuesta = getattr(cliente_autenticado(admin_a), metodo)(
        f"{URL}{cita_a.pk}/", {}, format="json"
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_integrity_error_no_relacionado_se_propaga(
    clinica_configurada,
    paciente_a,
    medico_citas,
):
    fallo = IntegrityError("fallo no relacionado")
    with patch.object(Cita.all_objects, "create", side_effect=fallo):
        with pytest.raises(IntegrityError) as error:
            crear_cita(
                clinica_configurada,
                {
                    "paciente_id": paciente_a.pk,
                    "medico_id": medico_citas.pk,
                    "fecha": date(2026, 11, 16),
                    "hora": time(8),
                    "motivo": "Control",
                },
            )
    assert error.value is fallo


@pytest.mark.django_db
def test_recepcionista_puede_cargar_selectores_de_cita(
    recepcionista_a,
    suscripcion_amplia,
    medico_citas,
):
    cliente = cliente_autenticado(recepcionista_a)
    especialidades = cliente.get("/api/v1/especialidades/")
    medicos = cliente.get(
        "/api/v1/medicos/", {"especialidad": medico_citas.especialidad_id}
    )

    assert especialidades.status_code == 200
    assert medicos.status_code == 200
    assert [item["id"] for item in medicos.data["results"]] == [medico_citas.pk]


@pytest.mark.django_db
def test_openapi_conserva_validaciones_s206():
    respuesta = Client().get("/api/schema/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    esquema = json.loads(respuesta.content)
    rutas = esquema["paths"]

    assert {"get", "post"} <= set(rutas["/api/v1/citas/"])
    assert set(rutas["/api/v1/citas/{id}/"]) == {"get"}
    assert set(rutas["/api/v1/citas/disponibilidad/"]) == {"get"}
    descripcion = rutas["/api/v1/citas/"]["post"]["description"]
    assert "PROGRAMADA" in descripcion
    assert "30 minutos" in descripcion
    assert "semiabierto" in descripcion
    assert "zona horaria" in descripcion
    assert "transacción" in descripcion
    operacion_crear = json.dumps(
        rutas["/api/v1/citas/"]["post"], ensure_ascii=False
    )
    operacion_disponibilidad = json.dumps(
        rutas["/api/v1/citas/disponibilidad/"]["get"], ensure_ascii=False
    )
    for codigo in (
        "fecha_cita_pasada",
        "hora_cita_pasada",
        "fuera_horario",
        "paciente_inactivo",
        "medico_inactivo",
        "horario_no_disponible",
        "paciente_no_disponible",
    ):
        assert codigo in operacion_crear
    assert "semiabiertos" in operacion_disponibilidad
    assert "aislamiento por clínica" in operacion_disponibilidad


@pytest.mark.django_db
def test_restriccion_real_de_medico_se_traduce_y_transaccion_sigue_utilizable(
    clinica_configurada,
    cita_a,
    medico_citas,
):
    otro_paciente = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-RACE-MED",
        nombre="Carrera",
        apellido="Médico",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000500",
    )
    with patch("apps.atencion.services._citas_que_bloquean", return_value=Cita.all_objects.none()):
        with pytest.raises(Conflicto) as error:
            crear_cita(
                clinica_configurada,
                {
                    "paciente_id": otro_paciente.pk,
                    "medico_id": medico_citas.pk,
                    "fecha": cita_a.fecha,
                    "hora": cita_a.hora,
                    "motivo": "Conflicto real",
                },
            )
    assert getattr(error.value, "codigo", None) == "horario_no_disponible"
    assert Cita.all_objects.count() == 1
    assert Paciente.all_objects.filter(pk=otro_paciente.pk).exists()


@pytest.mark.django_db
def test_restriccion_real_de_paciente_se_traduce(
    clinica_configurada,
    cita_a,
):
    personal = Personal.all_objects.create(
        clinica=clinica_configurada,
        ci="MED-RACE-PAC",
        nombre="Carrera",
        apellido="Paciente",
        telefono="70000501",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    otro_medico = Medico.all_objects.create(
        clinica=clinica_configurada,
        personal=personal,
        especialidad=cita_a.medico.especialidad,
        numero_colegiatura="COL-RACE-PAC",
    )
    HorarioAtencion.all_objects.create(
        medico=otro_medico,
        dia_semana=0,
        hora_inicio=time(8),
        hora_fin=time(10),
    )
    with patch("apps.atencion.services._citas_que_bloquean", return_value=Cita.all_objects.none()):
        with pytest.raises(Conflicto) as error:
            crear_cita(
                clinica_configurada,
                {
                    "paciente_id": cita_a.paciente_id,
                    "medico_id": otro_medico.pk,
                    "fecha": cita_a.fecha,
                    "hora": cita_a.hora,
                    "motivo": "Conflicto real",
                },
            )
    assert getattr(error.value, "codigo", None) == "paciente_no_disponible"
    assert Cita.all_objects.count() == 1


@pytest.mark.django_db
def test_clinica_inactiva_no_tiene_acceso(admin_a, suscripcion_amplia):
    admin_a.clinica.estado = False
    admin_a.clinica.save(update_fields=["estado"])
    respuesta = cliente_autenticado(admin_a).get(URL)
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "clinica_inactiva"

