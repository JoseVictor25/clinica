"""Pruebas API de S2-09: registro atómico de consultas médicas."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
import json
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections
from django.test import Client

from apps.atencion.models import Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta
from apps.atencion.services import crear_consulta
from apps.clinicas.models import Suscripcion
from apps.core.api_exceptions import Conflicto
from apps.core.seed_data import ROL_MEDICO
from apps.pacientes.models import HistoriaClinica
from tests.api.helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)


URL = "/api/v1/consultas/"
DATOS = {
    "motivo": "Dolor abdominal",
    "observacion": "Dolor presente desde hace dos días",
    "diagnostico": "Gastritis probable",
}


@pytest.fixture
def medico_consulta(clinica_configurada, medico_a):
    personal, medico = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="MED-CONSULTA-001",
        colegiatura="COL-CONSULTA-001",
    )
    return personal, medico


@pytest.fixture
def historia_consulta(paciente_a):
    return HistoriaClinica.all_objects.create(paciente=paciente_a)


@pytest.fixture
def cita_confirmada(clinica_configurada, paciente_a, medico_consulta, historia_consulta):
    return Cita.all_objects.create(
        clinica=clinica_configurada,
        paciente=paciente_a,
        medico=medico_consulta[1],
        fecha=date(2026, 11, 16),
        hora=time(8),
        estado=EstadoCita.CONFIRMADA,
        motivo="Dolor abdominal",
    )


def payload(cita, **cambios):
    return {"cita_id": cita.pk, **DATOS, **cambios}


@pytest.mark.django_db
def test_medico_registra_consulta_y_actualiza_cita_e_historia(
    medico_a, suscripcion_amplia, cita_confirmada, historia_consulta
):
    fecha_anterior = historia_consulta.fecha_ultima_actualizacion
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )

    assert respuesta.status_code == 201
    consulta = Consulta.all_objects.get(pk=respuesta.data["id"])
    assert consulta.clinica_id == cita_confirmada.clinica_id
    assert consulta.cita_id == cita_confirmada.pk
    assert consulta.medico_id == cita_confirmada.medico_id
    assert consulta.paciente_id == cita_confirmada.paciente_id
    assert (consulta.motivo, consulta.observacion, consulta.diagnostico) == (
        DATOS["motivo"], DATOS["observacion"], DATOS["diagnostico"]
    )
    assert not hasattr(consulta, "historia_id")
    cita_confirmada.refresh_from_db()
    historia_consulta.refresh_from_db()
    assert cita_confirmada.estado == EstadoCita.ATENDIDA
    assert historia_consulta.fecha_ultima_actualizacion > fecha_anterior
    assert respuesta.data["estado_cita"] == EstadoCita.ATENDIDA
    assert Receta.all_objects.count() == 0
    assert MedicamentoRecetado.all_objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["cita_id", "motivo", "observacion", "diagnostico"])
def test_campos_obligatorios_no_cambian_estado(
    medico_a, suscripcion_amplia, cita_confirmada, campo
):
    datos = payload(cita_confirmada)
    datos.pop(campo)
    respuesta = cliente_autenticado(medico_a).post(URL, datos, format="json")
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]
    cita_confirmada.refresh_from_db()
    assert cita_confirmada.estado == EstadoCita.CONFIRMADA
    assert not Consulta.all_objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("valor", [None, "abc", 0, -1])
def test_cita_id_debe_ser_entero_positivo(
    medico_a, suscripcion_amplia, cita_confirmada, valor
):
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada, cita_id=valor), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert "cita_id" in respuesta.data["detalles"]


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["motivo", "observacion", "diagnostico"])
@pytest.mark.parametrize("valor", ["", "   ", None])
def test_textos_invalidos_se_rechazan(
    medico_a, suscripcion_amplia, cita_confirmada, campo, valor
):
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada, **{campo: valor}), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "campo",
    ["clinica_id", "medico_id", "paciente_id", "historia_id", "fecha", "extra"],
)
def test_rechaza_campos_protegidos_y_desconocidos(
    medico_a, suscripcion_amplia, cita_confirmada, campo
):
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada, **{campo: 1}), format="json"
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado",
    [
        EstadoCita.PROGRAMADA,
        EstadoCita.ATENDIDA,
        EstadoCita.CANCELADA,
        EstadoCita.NO_ASISTIO,
    ],
)
def test_solo_acepta_cita_confirmada(
    medico_a, suscripcion_amplia, cita_confirmada, estado
):
    cita_confirmada.estado = estado
    cita_confirmada.save(update_fields=["estado"])
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cita_no_confirmada"
    assert not Consulta.all_objects.exists()


@pytest.mark.django_db
def test_consulta_duplicada_tiene_precedencia(
    medico_a, suscripcion_amplia, cita_confirmada
):
    cliente = cliente_autenticado(medico_a)
    assert cliente.post(URL, payload(cita_confirmada), format="json").status_code == 201
    segunda = cliente.post(URL, payload(cita_confirmada), format="json")
    assert segunda.status_code == 409
    assert segunda.data["codigo"] == "consulta_ya_registrada"
    assert Consulta.all_objects.filter(cita=cita_confirmada).count() == 1


@pytest.mark.django_db
def test_rechaza_paciente_inactivo(
    medico_a, suscripcion_amplia, cita_confirmada
):
    cita_confirmada.paciente.estado = False
    cita_confirmada.paciente.save(update_fields=["estado"])
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "paciente_inactivo"


@pytest.mark.django_db
def test_rechaza_historia_ausente(
    medico_a, suscripcion_amplia, cita_confirmada, historia_consulta
):
    historia_consulta.delete()
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "historia_no_disponible"


@pytest.mark.django_db
@pytest.mark.parametrize("recurso", ["medico", "personal"])
def test_rechaza_contexto_medico_inactivo(
    medico_a, suscripcion_amplia, cita_confirmada, medico_consulta, recurso
):
    objeto = medico_consulta[1] if recurso == "medico" else medico_consulta[0]
    objeto.estado = False
    objeto.save(update_fields=["estado"])
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_inactivo"


@pytest.mark.django_db
def test_medico_sin_vinculo_no_accede(
    medico_a, suscripcion_amplia, cita_confirmada
):
    cita_confirmada.medico.personal.usuario = None
    cita_confirmada.medico.personal.save(update_fields=["usuario"])
    respuesta = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_no_vinculado"


@pytest.mark.django_db
def test_medico_no_puede_atender_cita_de_otro_medico(
    medico_a, suscripcion_amplia, cita_confirmada, clinica_configurada
):
    otro_usuario = crear_usuario_con_rol(clinica_configurada, "otro_s209", ROL_MEDICO)
    crear_personal_medico(
        clinica_configurada, otro_usuario, ci="MED-OTRO-S209", colegiatura="COL-OTRO-S209"
    )
    respuesta = cliente_autenticado(otro_usuario).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 404
    assert respuesta.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
def test_oculta_cita_y_consulta_de_otra_clinica(
    medico_a,
    suscripcion_amplia,
    medico_consulta,
    clinica_b,
    admin_b,
    paciente_b,
):
    _, medico_b = crear_personal_medico(
        clinica_b,
        admin_b,
        ci="MED-B-S209",
        colegiatura="COL-B-S209",
    )
    cita_b = Cita.all_objects.create(
        clinica=clinica_b,
        paciente=paciente_b,
        medico=medico_b,
        fecha=date(2026, 11, 16),
        hora=time(9),
        estado=EstadoCita.CONFIRMADA,
        motivo="Cita de otra clínica",
    )
    consulta_b = Consulta.all_objects.create(
        clinica=clinica_b,
        cita=cita_b,
        paciente=paciente_b,
        medico=medico_b,
        **DATOS,
    )
    cliente = cliente_autenticado(medico_a)
    creacion = cliente.post(URL, payload(cita_b), format="json")
    detalle = cliente.get(f"{URL}{consulta_b.pk}/")
    assert creacion.status_code == 404
    assert creacion.data["codigo"] == "no_encontrado"
    assert detalle.status_code == 404
    assert detalle.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "usuario_fixture",
    ["admin_a", "recepcionista_a", "usuario_paciente_a", "conductor_a", "admin_sistema"],
)
def test_roles_no_autorizados_no_registran(
    request, usuario_fixture, suscripcion_amplia, cita_confirmada
):
    usuario = request.getfixturevalue(usuario_fixture)
    respuesta = cliente_autenticado(usuario).post(
        URL, payload(cita_confirmada), format="json"
    )
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_anonimo_no_accede(cliente, cita_confirmada):
    respuesta = cliente.post(URL, payload(cita_confirmada), format="json")
    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


@pytest.mark.django_db
def test_clinica_inactiva_y_suscripcion_vencida(
    medico_a, suscripcion_amplia, cita_confirmada
):
    cliente = cliente_autenticado(medico_a)
    medico_a.clinica.estado = False
    medico_a.clinica.save(update_fields=["estado"])
    inactiva = cliente.post(URL, payload(cita_confirmada), format="json")
    assert inactiva.status_code == 403
    assert inactiva.data["codigo"] == "clinica_inactiva"

    medico_a.clinica.estado = True
    medico_a.clinica.save(update_fields=["estado"])
    suscripcion_amplia.estado = Suscripcion.Estado.CANCELADA
    suscripcion_amplia.save(update_fields=["estado"])
    vencida = cliente.post(URL, payload(cita_confirmada), format="json")
    assert vencida.status_code == 403
    assert vencida.data["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_detalle_solo_del_medico_propietario(
    medico_a, suscripcion_amplia, cita_confirmada, clinica_configurada
):
    creada = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    detalle = cliente_autenticado(medico_a).get(f"{URL}{creada.data['id']}/")
    assert detalle.status_code == 200
    assert detalle.data["diagnostico"] == DATOS["diagnostico"]

    otro = crear_usuario_con_rol(clinica_configurada, "lector_otro_s209", ROL_MEDICO)
    crear_personal_medico(
        clinica_configurada, otro, ci="MED-LECTOR-S209", colegiatura="COL-LECTOR-S209"
    )
    oculto = cliente_autenticado(otro).get(f"{URL}{creada.data['id']}/")
    assert oculto.status_code == 404


@pytest.mark.django_db
def test_agenda_expone_consulta_de_forma_aditiva(
    medico_a, suscripcion_amplia, cita_confirmada
):
    cliente = cliente_autenticado(medico_a)
    antes = cliente.get("/api/v1/citas/mi-agenda/", {"fecha": cita_confirmada.fecha})
    assert antes.data["results"][0]["consulta_id"] is None
    assert antes.data["results"][0]["tiene_consulta"] is False

    creada = cliente.post(URL, payload(cita_confirmada), format="json")
    despues = cliente.get("/api/v1/citas/mi-agenda/", {"fecha": cita_confirmada.fecha})
    item = despues.data["results"][0]
    assert item["consulta_id"] == creada.data["id"]
    assert item["tiene_consulta"] is True
    assert item["estado"] == EstadoCita.ATENDIDA


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
def test_metodos_de_modificacion_no_expuestos(
    metodo, medico_a, suscripcion_amplia, cita_confirmada
):
    creada = cliente_autenticado(medico_a).post(
        URL, payload(cita_confirmada), format="json"
    )
    respuesta = getattr(cliente_autenticado(medico_a), metodo)(
        f"{URL}{creada.data['id']}/", {}, format="json"
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_no_expone_listado(medico_a, suscripcion_amplia, medico_consulta):
    respuesta = cliente_autenticado(medico_a).get(URL)
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_fallo_en_consulta_hace_rollback(
    medico_a, suscripcion_amplia, cita_confirmada, historia_consulta
):
    fecha_anterior = historia_consulta.fecha_ultima_actualizacion
    with patch.object(Consulta.all_objects, "create", side_effect=RuntimeError("fallo")):
        with pytest.raises(RuntimeError):
            crear_consulta(
                usuario=medico_a,
                clinica=medico_a.clinica,
                datos=payload(cita_confirmada),
            )
    cita_confirmada.refresh_from_db()
    historia_consulta.refresh_from_db()
    assert cita_confirmada.estado == EstadoCita.CONFIRMADA
    assert historia_consulta.fecha_ultima_actualizacion == fecha_anterior


@pytest.mark.django_db
def test_fallo_en_historia_revierte_consulta(
    medico_a, suscripcion_amplia, cita_confirmada, historia_consulta
):
    with patch.object(HistoriaClinica, "save", side_effect=RuntimeError("fallo")):
        with pytest.raises(RuntimeError):
            crear_consulta(
                usuario=medico_a,
                clinica=medico_a.clinica,
                datos=payload(cita_confirmada),
            )
    cita_confirmada.refresh_from_db()
    assert cita_confirmada.estado == EstadoCita.CONFIRMADA
    assert not Consulta.all_objects.exists()


@pytest.mark.django_db
def test_fallo_en_cita_revierte_consulta_e_historia(
    medico_a, suscripcion_amplia, cita_confirmada, historia_consulta
):
    fecha_anterior = historia_consulta.fecha_ultima_actualizacion
    with patch.object(Cita, "save", side_effect=RuntimeError("fallo")):
        with pytest.raises(RuntimeError):
            crear_consulta(
                usuario=medico_a,
                clinica=medico_a.clinica,
                datos=payload(cita_confirmada),
            )
    cita_confirmada.refresh_from_db()
    historia_consulta.refresh_from_db()
    assert cita_confirmada.estado == EstadoCita.CONFIRMADA
    assert historia_consulta.fecha_ultima_actualizacion == fecha_anterior
    assert not Consulta.all_objects.exists()


@pytest.mark.django_db
def test_integrity_error_inesperado_se_propaga(
    medico_a, suscripcion_amplia, cita_confirmada
):
    fallo = IntegrityError("fallo inesperado")
    with patch.object(Consulta.all_objects, "create", side_effect=fallo):
        with pytest.raises(IntegrityError) as error:
            crear_consulta(
                usuario=medico_a,
                clinica=medico_a.clinica,
                datos=payload(cita_confirmada),
            )
    assert error.value is fallo


def _crear_concurrente(usuario_id, clinica_id, datos, barrera):
    from apps.clinicas.models import Clinica
    from apps.seguridad.models import Usuario

    close_old_connections()
    try:
        usuario = Usuario.objects.get(pk=usuario_id)
        clinica = Clinica.objects.get(pk=clinica_id)
        barrera.wait(timeout=5)
        consulta = crear_consulta(usuario=usuario, clinica=clinica, datos=datos)
        return "ok", consulta.pk
    except Conflicto as error:
        return "conflicto", error.codigo
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_dos_solicitudes_simultaneas_crean_una_consulta(
    medico_a, cita_confirmada
):
    assert connection.vendor == "postgresql"
    barrera = Barrier(2)
    datos = payload(cita_confirmada)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [
            ejecutor.submit(
                _crear_concurrente,
                medico_a.pk,
                medico_a.clinica_id,
                datos,
                barrera,
            )
            for _ in range(2)
        ]
        resultados = [futuro.result(timeout=10) for futuro in futuros]
    assert sorted(resultado[0] for resultado in resultados) == ["conflicto", "ok"]
    assert ("conflicto", "consulta_ya_registrada") in resultados
    assert Consulta.all_objects.filter(cita=cita_confirmada).count() == 1


@pytest.mark.django_db
def test_openapi_documenta_solo_creacion_y_detalle():
    respuesta = Client().get("/api/schema/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    esquema = json.loads(respuesta.content)
    paths = esquema["paths"]
    assert set(paths["/api/v1/consultas/"]) == {"post"}
    assert set(paths["/api/v1/consultas/{id}/"]) == {"get"}
    documento = json.dumps(esquema, ensure_ascii=False)
    for codigo in (
        "consulta_ya_registrada",
        "cita_no_confirmada",
        "historia_no_disponible",
        "medico_no_vinculado",
    ):
        assert codigo in documento
    assert "consulta_id" in documento
