"""Pruebas API de S2-10: recetas y advertencias de alergias."""

from datetime import date, time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections

from apps.atencion.models import (
    Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta,
)
from apps.atencion.services import crear_receta
from apps.pacientes.models import Alergia, HistoriaClinica, Severidad, TipoAlergia
from tests.api.helpers import cliente_autenticado, crear_personal_medico


@pytest.fixture
def contexto_receta(clinica_configurada, medico_a, paciente_a):
    personal, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="MED-REC-001", colegiatura="COL-REC-001"
    )
    historia = HistoriaClinica.all_objects.create(paciente=paciente_a)
    cita = Cita.all_objects.create(
        clinica=clinica_configurada, paciente=paciente_a, medico=medico,
        fecha=date(2026, 11, 16), hora=time(8), estado=EstadoCita.ATENDIDA,
        motivo="Control",
    )
    consulta = Consulta.all_objects.create(
        clinica=clinica_configurada, cita=cita, medico=medico, paciente=paciente_a,
        motivo="Control", observacion="Estable", diagnostico="Resfrío",
    )
    return medico_a, personal, medico, paciente_a, historia, cita, consulta


def datos(**cambios):
    base = {
        "indicaciones": "Tomar con alimentos",
        "medicamentos": [{
            "nombre_medicamento": "Paracetamol", "dosis": "500 mg",
            "frecuencia": "Cada 8 horas", "duracion": "3 días",
        }],
    }
    base.update(cambios)
    return base


def url_crear(consulta):
    return f"/api/v1/consultas/{consulta.pk}/recetas/"


@pytest.mark.django_db
def test_crea_receta_completa_y_permite_varias(contexto_receta, suscripcion_amplia):
    usuario, _, _, _, historia, cita, consulta = contexto_receta
    cliente = cliente_autenticado(usuario)
    historia_fecha = historia.fecha_ultima_actualizacion
    primera = cliente.post(url_crear(consulta), datos(), format="json")
    segunda = cliente.post(url_crear(consulta), datos(indicaciones="Otra"), format="json")
    assert primera.status_code == segunda.status_code == 201
    assert Receta.all_objects.filter(consulta=consulta).count() == 2
    assert primera.data["medicamentos"][0]["nombre_medicamento"] == "Paracetamol"
    cita.refresh_from_db(); historia.refresh_from_db(); consulta.refresh_from_db()
    assert cita.estado == EstadoCita.ATENDIDA
    assert historia.fecha_ultima_actualizacion == historia_fecha
    assert consulta.diagnostico == "Resfrío"


@pytest.mark.django_db
def test_crea_varios_medicamentos_en_orden(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    medicamentos = [
        {"nombre_medicamento": "A", "dosis": "1", "frecuencia": "1", "duracion": "1"},
        {"nombre_medicamento": "B", "dosis": "2", "frecuencia": "2", "duracion": "2"},
    ]
    respuesta = cliente_autenticado(usuario).post(
        url_crear(consulta), datos(medicamentos=medicamentos), format="json"
    )
    assert respuesta.status_code == 201
    assert [item["nombre_medicamento"] for item in respuesta.data["medicamentos"]] == ["A", "B"]


@pytest.mark.django_db
@pytest.mark.parametrize("valor", [None, [], "no-lista"])
def test_rechaza_medicamentos_invalidos(contexto_receta, suscripcion_amplia, valor):
    usuario, *_, consulta = contexto_receta
    respuesta = cliente_autenticado(usuario).post(
        url_crear(consulta), datos(medicamentos=valor), format="json"
    )
    assert respuesta.status_code == 400
    assert not Receta.all_objects.exists()


@pytest.mark.django_db
def test_rechaza_medicamentos_ausentes(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    payload = datos(); payload.pop("medicamentos")
    respuesta = cliente_autenticado(usuario).post(url_crear(consulta), payload, format="json")
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "medicamentos_requeridos"


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["nombre_medicamento", "dosis", "frecuencia", "duracion"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_rechaza_campos_vacios(contexto_receta, suscripcion_amplia, campo, valor):
    usuario, *_, consulta = contexto_receta
    item = datos()["medicamentos"][0]; item[campo] = valor
    respuesta = cliente_autenticado(usuario).post(
        url_crear(consulta), datos(medicamentos=[item]), format="json"
    )
    assert respuesta.status_code == 400
    assert campo in respuesta.data["detalles"]["medicamentos"][0]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [
    {"campo": "prohibido", "medicamentos": []},
    {"consulta_id": 1, "medicamentos": []},
])
def test_rechaza_campos_desconocidos(contexto_receta, suscripcion_amplia, payload):
    usuario, *_, consulta = contexto_receta
    respuesta = cliente_autenticado(usuario).post(url_crear(consulta), payload, format="json")
    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_rechaza_campo_desconocido_anidado(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    item = {**datos()["medicamentos"][0], "receta_id": 99}
    respuesta = cliente_autenticado(usuario).post(
        url_crear(consulta), datos(medicamentos=[item]), format="json"
    )
    assert respuesta.status_code == 400
    assert "receta_id" in respuesta.data["detalles"]["medicamentos"][0]


@pytest.mark.django_db
def test_exige_consulta_atendida(contexto_receta, suscripcion_amplia):
    usuario, *_, cita, consulta = contexto_receta
    cita.estado = EstadoCita.CONFIRMADA; cita.save(update_fields=["estado"])
    respuesta = cliente_autenticado(usuario).post(url_crear(consulta), datos(), format="json")
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "consulta_no_atendida"


@pytest.mark.django_db
def test_advertencia_exacta_normalizada_y_no_bloqueante(contexto_receta, suscripcion_amplia):
    usuario, _, _, _, historia, _, consulta = contexto_receta
    alergia = Alergia.all_objects.create(
        historia=historia, nombre="  PARACETAMOL  ", tipo=TipoAlergia.MEDICAMENTO,
        severidad=Severidad.GRAVE,
    )
    respuesta = cliente_autenticado(usuario).post(url_crear(consulta), datos(), format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["advertencias_alergia"] == [{
        "alergia_id": alergia.pk, "nombre_alergia": alergia.nombre,
        "severidad": Severidad.GRAVE, "medicamento": "Paracetamol",
        "mensaje": "El medicamento Paracetamol coincide con la alergia medicamentosa   PARACETAMOL  .",
    }]


@pytest.mark.django_db
@pytest.mark.parametrize("tipo,nombre", [
    (TipoAlergia.ALIMENTO, "Paracetamol"),
    (TipoAlergia.MEDICAMENTO, "Paracetamol 500 mg"),
    (TipoAlergia.MEDICAMENTO, "Para"),
])
def test_no_genera_falsos_positivos(contexto_receta, suscripcion_amplia, tipo, nombre):
    usuario, _, _, _, historia, _, consulta = contexto_receta
    Alergia.all_objects.create(historia=historia, nombre=nombre, tipo=tipo, severidad=Severidad.LEVE)
    respuesta = cliente_autenticado(usuario).post(url_crear(consulta), datos(), format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["advertencias_alergia"] == []


@pytest.mark.django_db
def test_get_recalcula_advertencias_actuales(contexto_receta, suscripcion_amplia):
    usuario, _, _, _, historia, _, consulta = contexto_receta
    cliente = cliente_autenticado(usuario)
    creada = cliente.post(url_crear(consulta), datos(), format="json")
    assert creada.data["advertencias_alergia"] == []
    Alergia.all_objects.create(
        historia=historia, nombre="Paracetamol", tipo=TipoAlergia.MEDICAMENTO,
        severidad=Severidad.MODERADA,
    )
    detalle = cliente.get(f"/api/v1/recetas/{creada.data['id']}/")
    assert detalle.status_code == 200
    assert len(detalle.data["advertencias_alergia"]) == 1


@pytest.mark.django_db
def test_detalle_consulta_incluye_resumenes(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    cliente = cliente_autenticado(usuario)
    receta = cliente.post(url_crear(consulta), datos(), format="json")
    detalle = cliente.get(f"/api/v1/consultas/{consulta.pk}/")
    assert detalle.status_code == 200
    assert detalle.data["recetas"][0]["id"] == receta.data["id"]
    assert detalle.data["recetas"][0]["cantidad_medicamentos"] == 1


@pytest.mark.django_db
def test_otro_rol_y_anonimo_no_acceden(contexto_receta, suscripcion_amplia, admin_a, cliente):
    _, *_, consulta = contexto_receta
    assert cliente.post(url_crear(consulta), datos(), format="json").status_code == 401
    assert cliente_autenticado(admin_a).post(
        url_crear(consulta), datos(), format="json"
    ).status_code == 403


@pytest.mark.django_db
def test_consulta_y_receta_ajenas_se_ocultan(contexto_receta, suscripcion_amplia, admin_a):
    usuario, *_, consulta = contexto_receta
    creada = cliente_autenticado(usuario).post(url_crear(consulta), datos(), format="json")
    assert cliente_autenticado(admin_a).get(
        f"/api/v1/recetas/{creada.data['id']}/"
    ).status_code == 403


@pytest.mark.django_db
def test_rollback_si_falla_medicamento(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    with patch.object(MedicamentoRecetado.all_objects, "create", side_effect=IntegrityError("fallo")):
        with pytest.raises(IntegrityError):
            crear_receta(
                usuario=usuario, clinica=usuario.clinica, consulta_id=consulta.pk,
                datos=datos(),
            )
    assert not Receta.all_objects.exists()
    assert not MedicamentoRecetado.all_objects.exists()


def _crear_receta_concurrente(usuario_id, clinica_id, consulta_id, barrera, numero):
    from apps.clinicas.models import Clinica
    from apps.seguridad.models import Usuario

    close_old_connections()
    try:
        usuario = Usuario.objects.get(pk=usuario_id)
        clinica = Clinica.objects.get(pk=clinica_id)
        barrera.wait(timeout=5)
        receta = crear_receta(
            usuario=usuario,
            clinica=clinica,
            consulta_id=consulta_id,
            datos=datos(indicaciones=f"Receta {numero}"),
        )
        return receta.pk
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_dos_recetas_concurrentes_son_completas(contexto_receta):
    assert connection.vendor == "postgresql"
    usuario, *_, consulta = contexto_receta
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [
            ejecutor.submit(
                _crear_receta_concurrente,
                usuario.pk,
                usuario.clinica_id,
                consulta.pk,
                barrera,
                numero,
            )
            for numero in (1, 2)
        ]
        ids = [futuro.result(timeout=10) for futuro in futuros]
    assert len(set(ids)) == 2
    assert Receta.all_objects.filter(consulta=consulta).count() == 2
    assert MedicamentoRecetado.all_objects.filter(receta__consulta=consulta).count() == 2


@pytest.mark.django_db
def test_metodos_y_listado_no_expuestos(contexto_receta, suscripcion_amplia):
    usuario, *_, consulta = contexto_receta
    cliente = cliente_autenticado(usuario)
    creada = cliente.post(url_crear(consulta), datos(), format="json")
    detalle = f"/api/v1/recetas/{creada.data['id']}/"
    assert cliente.get("/api/v1/recetas/").status_code == 404
    for metodo in (cliente.post, cliente.put, cliente.patch, cliente.delete):
        assert metodo(detalle, {}, format="json").status_code == 405


@pytest.mark.django_db
def test_openapi_documenta_solo_endpoints_s210(cliente):
    esquema = cliente.get("/api/schema/?format=json").json()["paths"]
    assert set(esquema["/api/v1/consultas/{consulta_id}/recetas/"]) == {"post"}
    assert set(esquema["/api/v1/recetas/{id}/"]) == {"get"}
    assert "/api/v1/recetas/" not in esquema
