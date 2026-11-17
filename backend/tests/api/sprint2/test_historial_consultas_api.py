"""Pruebas API de S2-11: historial consolidado de consultas."""

from datetime import datetime, timedelta
import json

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.atencion.models import Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta
from apps.clinicas.models import Suscripcion
from apps.core.seed_data import (
    ROL_ADMIN_CLINICA,
    ROL_CONDUCTOR,
    ROL_MEDICO,
    ROL_PACIENTE,
    ROL_RECEPCIONISTA,
)
from apps.pacientes.models import HistoriaClinica
from apps.personal.models import Medico
from tests.api.helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)


def instante(dias, hora=10):
    fecha = timezone.localdate() + timedelta(days=dias)
    return timezone.make_aware(datetime.combine(fecha, datetime.min.time().replace(hour=hora)))


@pytest.fixture
def historial_contexto(clinica_configurada, medico_a, paciente_a, suscripcion_amplia):
    personal, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="MED-HIST-1", colegiatura="COL-HIST-1"
    )
    otro_usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_historial_2", ROL_MEDICO
    )
    _, otro_medico = crear_personal_medico(
        clinica_configurada, otro_usuario, ci="MED-HIST-2", colegiatura="COL-HIST-2",
        nombre="Otro", apellido="Médico",
    )
    historia = HistoriaClinica.all_objects.create(paciente=paciente_a)
    cita = Cita.all_objects.create(
        clinica=clinica_configurada, paciente=paciente_a, medico=medico,
        fecha=timezone.localdate(), hora=datetime.min.time().replace(hour=9),
        estado=EstadoCita.ATENDIDA, motivo="Control",
    )
    propia = Consulta.all_objects.create(
        clinica=clinica_configurada, cita=cita, medico=medico, paciente=paciente_a,
        fecha=instante(0, 10), motivo="Control", observacion="Estable",
        diagnostico="Diagnóstico propio",
    )
    ajena = Consulta.all_objects.create(
        clinica=clinica_configurada, cita=None, medico=otro_medico, paciente=paciente_a,
        fecha=instante(-2, 11), motivo="Urgencia", observacion="Sin cita",
        diagnostico="Diagnóstico anterior",
    )
    receta_propia = Receta.all_objects.create(consulta=propia, indicaciones="Con comida")
    MedicamentoRecetado.all_objects.create(
        receta=receta_propia, nombre_medicamento="A", dosis="1",
        frecuencia="Cada día", duracion="2 días",
    )
    receta_ajena = Receta.all_objects.create(consulta=ajena, indicaciones="Reposo")
    MedicamentoRecetado.all_objects.create(
        receta=receta_ajena, nombre_medicamento="B", dosis="2",
        frecuencia="Cada noche", duracion="3 días",
    )
    return {
        "usuario": medico_a, "medico": medico, "otro_usuario": otro_usuario,
        "otro_medico": otro_medico, "paciente": paciente_a, "historia": historia,
        "propia": propia, "ajena": ajena, "receta_propia": receta_propia,
        "receta_ajena": receta_ajena,
    }


def url(paciente):
    return f"/api/v1/pacientes/{paciente.pk}/historial-consultas/"


@pytest.mark.django_db
def test_historial_consolida_consultas_citas_recetas_y_medicamentos(historial_contexto):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 200
    assert respuesta.data["paciente"] == {
        "id": ctx["paciente"].pk, "ci": ctx["paciente"].ci,
        "nombre": ctx["paciente"].nombre, "apellido": ctx["paciente"].apellido,
        "sexo": ctx["paciente"].sexo,
        "fecha_nacimiento": str(ctx["paciente"].fecha_nacimiento),
        "estado": True,
    }
    assert [item["id"] for item in respuesta.data["results"]] == [
        ctx["propia"].pk, ctx["ajena"].pk,
    ]
    propia, ajena = respuesta.data["results"]
    assert propia["cita"]["id"] == ctx["propia"].cita_id
    assert ajena["cita"] is None
    assert propia["recetas"][0]["puede_ver_detalle"] is True
    assert ajena["recetas"][0]["puede_ver_detalle"] is False
    assert propia["recetas"][0]["medicamentos"][0]["nombre_medicamento"] == "A"
    assert ajena["medico"]["id"] == ctx["otro_medico"].pk


@pytest.mark.django_db
def test_historial_vacio_es_valido(historial_contexto):
    ctx = historial_contexto
    MedicamentoRecetado.all_objects.all().delete()
    Receta.all_objects.all().delete()
    Consulta.all_objects.all().delete()
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 0
    assert respuesta.data["results"] == []


@pytest.mark.django_db
@pytest.mark.parametrize("ordering,esperados", [
    ("-fecha", ["propia", "ajena"]),
    ("fecha", ["ajena", "propia"]),
])
def test_ordenamiento_estable(historial_contexto, ordering, esperados):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(
        url(ctx["paciente"]), {"ordering": ordering}
    )
    assert [item["id"] for item in respuesta.data["results"]] == [ctx[n].pk for n in esperados]


@pytest.mark.django_db
def test_filtros_fecha_inclusivos(historial_contexto):
    ctx = historial_contexto
    fecha = timezone.localdate().isoformat()
    respuesta = cliente_autenticado(ctx["usuario"]).get(
        url(ctx["paciente"]), {"fecha_desde": fecha, "fecha_hasta": fecha}
    )
    assert respuesta.status_code == 200
    assert [item["id"] for item in respuesta.data["results"]] == [ctx["propia"].pk]


@pytest.mark.django_db
def test_filtra_por_medico_del_tenant(historial_contexto):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(
        url(ctx["paciente"]), {"medico_id": ctx["otro_medico"].pk}
    )
    assert [item["id"] for item in respuesta.data["results"]] == [ctx["ajena"].pk]


@pytest.mark.django_db
@pytest.mark.parametrize("parametros,campo", [
    ({"fecha_desde": "2026-12-02", "fecha_hasta": "2026-12-01"}, "fecha_hasta"),
    ({"fecha_desde": "invalida"}, "fecha_desde"),
    ({"medico_id": "abc"}, "medico_id"),
    ({"ordering": "diagnostico"}, "ordering"),
    ({"page": 0}, "page"),
    ({"page_size": 101}, "page_size"),
    ({"desconocido": "x"}, "desconocido"),
])
def test_rechaza_filtros_invalidos(historial_contexto, parametros, campo):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]), parametros)
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
def test_pagina_y_conserva_metadatos_paciente(historial_contexto):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(
        url(ctx["paciente"]), {"page": 2, "page_size": 1}
    )
    assert respuesta.status_code == 200
    assert respuesta.data["paciente"]["id"] == ctx["paciente"].pk
    assert respuesta.data["count"] == 2
    assert len(respuesta.data["results"]) == 1


@pytest.mark.django_db
def test_paciente_inactivo_y_sin_historia(historial_contexto):
    ctx = historial_contexto
    ctx["paciente"].estado = False
    ctx["paciente"].save(update_fields=["estado"])
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "paciente_inactivo"
    ctx["paciente"].estado = True
    ctx["paciente"].save(update_fields=["estado"])
    ctx["historia"].delete()
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "historia_no_disponible"


@pytest.mark.django_db
def test_otro_tenant_no_ve_paciente(historial_contexto, paciente_b):
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(paciente_b))
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
def test_medico_filtro_de_otro_tenant_devuelve_404(
    historial_contexto, clinica_b, suscripcion_b, usuario_b
):
    _, medico_b = crear_personal_medico(
        clinica_b, usuario_b, ci="MED-HIST-B", colegiatura="COL-HIST-B"
    )
    ctx = historial_contexto
    respuesta = cliente_autenticado(ctx["usuario"]).get(
        url(ctx["paciente"]), {"medico_id": medico_b.pk}
    )
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
def test_anonimo_y_recepcionista_no_acceden(historial_contexto, cliente):
    ctx = historial_contexto
    assert cliente.get(url(ctx["paciente"])).status_code == 401
    recepcionista = crear_usuario_con_rol(
        ctx["paciente"].clinica, "recep_historial", ROL_RECEPCIONISTA
    )
    assert cliente_autenticado(recepcionista).get(url(ctx["paciente"])).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [ROL_ADMIN_CLINICA, ROL_PACIENTE, ROL_CONDUCTOR])
def test_roles_no_medicos_no_acceden(historial_contexto, rol):
    ctx = historial_contexto
    usuario = crear_usuario_con_rol(
        ctx["paciente"].clinica, f"sin_acceso_{rol[:3]}", rol
    )
    assert cliente_autenticado(usuario).get(url(ctx["paciente"])).status_code == 403


@pytest.mark.django_db
def test_medico_sin_perfil_es_rechazado(historial_contexto):
    ctx = historial_contexto
    usuario = crear_usuario_con_rol(
        ctx["paciente"].clinica, "medico_sin_perfil_hist", ROL_MEDICO
    )
    respuesta = cliente_autenticado(usuario).get(url(ctx["paciente"]))
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_no_vinculado"


@pytest.mark.django_db
def test_medico_inactivo_no_accede(historial_contexto):
    ctx = historial_contexto
    ctx["medico"].estado = False
    ctx["medico"].save(update_fields=["estado"])
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_inactivo"


@pytest.mark.django_db
def test_personal_inactivo_no_accede(historial_contexto):
    ctx = historial_contexto
    ctx["medico"].personal.estado = False
    ctx["medico"].personal.save(update_fields=["estado"])
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_inactivo"


@pytest.mark.django_db
def test_clinica_inactiva_y_suscripcion_vencida_no_acceden(
    historial_contexto, suscripcion_amplia
):
    ctx = historial_contexto
    ctx["paciente"].clinica.estado = False
    ctx["paciente"].clinica.save(update_fields=["estado"])
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "clinica_inactiva"
    ctx["paciente"].clinica.estado = True
    ctx["paciente"].clinica.save(update_fields=["estado"])
    suscripcion_amplia.estado = Suscripcion.Estado.CANCELADA
    suscripcion_amplia.save(update_fields=["estado"])
    respuesta = cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_lectura_no_modifica_historia(historial_contexto):
    ctx = historial_contexto
    fecha = ctx["historia"].fecha_ultima_actualizacion
    cliente_autenticado(ctx["usuario"]).get(url(ctx["paciente"]))
    ctx["historia"].refresh_from_db()
    assert ctx["historia"].fecha_ultima_actualizacion == fecha


@pytest.mark.django_db
def test_consultas_sql_no_crecen_con_recetas(historial_contexto):
    ctx = historial_contexto
    cliente = cliente_autenticado(ctx["usuario"])
    with CaptureQueriesContext(connection) as capturadas:
        respuesta = cliente.get(url(ctx["paciente"]))
    assert respuesta.status_code == 200
    assert len(capturadas) <= 16


@pytest.mark.django_db
def test_metodos_de_escritura_no_permitidos(historial_contexto):
    ctx = historial_contexto
    cliente = cliente_autenticado(ctx["usuario"])
    for metodo in (cliente.post, cliente.put, cliente.patch, cliente.delete):
        assert metodo(url(ctx["paciente"]), {}, format="json").status_code == 405


@pytest.mark.django_db
def test_openapi_documenta_solo_get():
    respuesta = Client().get("/api/schema/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    paths = json.loads(respuesta.content)["paths"]
    ruta = "/api/v1/pacientes/{paciente_id}/historial-consultas/"
    assert set(paths[ruta]) == {"get"}
    parametros = {p["name"] for p in paths[ruta]["get"]["parameters"]}
    assert {"paciente_id", "fecha_desde", "fecha_hasta", "medico_id", "ordering", "page", "page_size"} <= parametros
