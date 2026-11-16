"""S2-13: recorrido integrado paciente → atención → portal."""

from datetime import date, datetime, time

import pytest
from django.utils import timezone

from apps.atencion.models import Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta
from apps.pacientes.models import Alergia, Enfermedad, HistoriaClinica, Paciente
from apps.personal.models import HorarioAtencion
from tests.api.helpers import cliente_autenticado, crear_personal_medico


FECHA_ATENCION = date(2026, 11, 16)  # lunes, alineado con el reloj de Sprint 2


def _aware(fecha, hora):
    return timezone.make_aware(
        datetime.combine(fecha, hora), timezone.get_current_timezone()
    )


@pytest.mark.django_db
def test_flujo_clinico_completo_hasta_portal(
    clinica_configurada,
    suscripcion_amplia,
    admin_a,
    recepcionista_a,
    medico_a,
    usuario_paciente_a,
):
    """Integra S2-01 a S2-12 usando la API para el comportamiento clínico."""

    # Personal, médico y horario son precondiciones administrativas del flujo.
    _, medico = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="MED-E2E-S2",
        colegiatura="COL-E2E-S2",
        nombre="Elena",
        apellido="Flujo",
    )
    HorarioAtencion.all_objects.create(
        medico=medico,
        dia_semana=FECHA_ATENCION.weekday(),
        hora_inicio=time(8),
        hora_fin=time(10),
    )

    recepcion = cliente_autenticado(recepcionista_a)
    medico_cliente = cliente_autenticado(medico_a)
    admin = cliente_autenticado(admin_a)

    # S2-01/S2-02: alta de paciente e historia automática, sin elegir tenant.
    paciente_respuesta = recepcion.post(
        "/api/v1/pacientes/",
        {
            "ci": "PAC-E2E-S2",
            "nombre": "Ana",
            "apellido": "Integración",
            "sexo": "F",
            "fecha_nacimiento": "1992-04-15",
            "telefono": "70009901",
            "email": "ana.integracion@example.test",
            "estado": True,
        },
        format="json",
    )
    assert paciente_respuesta.status_code == 201, paciente_respuesta.data
    paciente_id = paciente_respuesta.data["id"]
    paciente = Paciente.all_objects.get(pk=paciente_id)
    assert paciente.clinica_id == clinica_configurada.pk
    historias = HistoriaClinica.all_objects.filter(paciente=paciente)
    assert historias.count() == 1
    historia = historias.get()
    historia.observaciones_generales = "Antecedentes revisados en la demostración."
    historia.save(update_fields=["observaciones_generales"])

    # S2-03/S2-04: antecedentes registrados por el médico.
    enfermedad_respuesta = medico_cliente.post(
        f"/api/v1/pacientes/{paciente_id}/enfermedades/",
        {
            "nombre": "Asma",
            "tipo": "CRONICA",
            "severidad": "LEVE",
            "fecha_deteccion": "2025-03-10",
        },
        format="json",
    )
    assert enfermedad_respuesta.status_code == 201, enfermedad_respuesta.data
    alergia_respuesta = medico_cliente.post(
        f"/api/v1/pacientes/{paciente_id}/alergias/",
        {
            "nombre": "Paracetamol",
            "tipo": "MEDICAMENTO",
            "severidad": "GRAVE",
            "descripcion": "Reacción documentada para la prueba integrada.",
        },
        format="json",
    )
    assert alergia_respuesta.status_code == 201, alergia_respuesta.data
    assert Enfermedad.all_objects.get(pk=enfermedad_respuesta.data["id"]).historia_id == historia.pk
    assert Alergia.all_objects.get(pk=alergia_respuesta.data["id"]).historia_id == historia.pk

    enfermedad_rechazada = recepcion.post(
        f"/api/v1/pacientes/{paciente_id}/enfermedades/",
        {
            "nombre": "No autorizada",
            "tipo": "OTRA",
            "severidad": "LEVE",
            "fecha_deteccion": "2025-03-10",
        },
        format="json",
    )
    assert enfermedad_rechazada.status_code == 403
    assert not Enfermedad.all_objects.filter(nombre="No autorizada").exists()

    # S2-05/S2-06: disponibilidad real y reserva del primer bloque.
    parametros = {
        "paciente_id": paciente_id,
        "medico_id": medico.pk,
        "fecha": FECHA_ATENCION.isoformat(),
    }
    disponibilidad = recepcion.get("/api/v1/citas/disponibilidad/", parametros)
    assert disponibilidad.status_code == 200, disponibilidad.data
    assert disponibilidad.data["horarios"] == ["08:00", "08:30", "09:00", "09:30"]
    hora_elegida = disponibilidad.data["horarios"][0]

    cita_respuesta = recepcion.post(
        "/api/v1/citas/",
        {
            **parametros,
            "hora": hora_elegida,
            "motivo": "Control integral del Sprint 2",
        },
        format="json",
    )
    assert cita_respuesta.status_code == 201, cita_respuesta.data
    cita_id = cita_respuesta.data["id"]
    assert cita_respuesta.data["estado"] == EstadoCita.PROGRAMADA
    assert cita_respuesta.data["paciente_id"] == paciente_id
    assert cita_respuesta.data["medico_id"] == medico.pk
    posterior = recepcion.get("/api/v1/citas/disponibilidad/", parametros)
    assert hora_elegida not in posterior.data["horarios"]

    # S2-07/S2-08: confirmación y aparición en la agenda propia.
    confirmada = recepcion.post(
        f"/api/v1/citas/{cita_id}/confirmar/", {}, format="json"
    )
    assert confirmada.status_code == 200, confirmada.data
    assert confirmada.data["estado"] == EstadoCita.CONFIRMADA
    agenda = medico_cliente.get(
        "/api/v1/citas/mi-agenda/", {"fecha": FECHA_ATENCION.isoformat()}
    )
    assert agenda.status_code == 200, agenda.data
    assert [item["id"] for item in agenda.data["results"]] == [cita_id]

    # S2-09: consulta y transición atómica a ATENDIDA.
    consulta_respuesta = medico_cliente.post(
        "/api/v1/consultas/",
        {
            "cita_id": cita_id,
            "motivo": "Control respiratorio",
            "observacion": "Paciente estable durante la atención.",
            "diagnostico": "Asma controlada",
        },
        format="json",
    )
    assert consulta_respuesta.status_code == 201, consulta_respuesta.data
    consulta_id = consulta_respuesta.data["id"]
    cita = Cita.all_objects.get(pk=cita_id)
    assert cita.estado == EstadoCita.ATENDIDA
    assert Consulta.all_objects.filter(cita=cita).count() == 1
    duplicada = medico_cliente.post(
        "/api/v1/consultas/",
        {
            "cita_id": cita_id,
            "motivo": "Duplicada",
            "observacion": "No debe persistir",
            "diagnostico": "No debe persistir",
        },
        format="json",
    )
    assert duplicada.status_code == 409
    assert duplicada.data["codigo"] == "consulta_ya_registrada"
    assert Consulta.all_objects.filter(cita=cita).count() == 1

    # S2-10: receta atómica, orden y advertencia informativa de alergia.
    receta_respuesta = medico_cliente.post(
        f"/api/v1/consultas/{consulta_id}/recetas/",
        {
            "indicaciones": "Tomar según indicación y acudir a control.",
            "medicamentos": [
                {
                    "nombre_medicamento": "Paracetamol",
                    "dosis": "500 mg",
                    "frecuencia": "Cada 8 horas",
                    "duracion": "3 días",
                },
                {
                    "nombre_medicamento": "Salbutamol",
                    "dosis": "2 inhalaciones",
                    "frecuencia": "Según necesidad",
                    "duracion": "5 días",
                },
            ],
        },
        format="json",
    )
    assert receta_respuesta.status_code == 201, receta_respuesta.data
    receta_id = receta_respuesta.data["id"]
    assert [m["nombre_medicamento"] for m in receta_respuesta.data["medicamentos"]] == [
        "Paracetamol", "Salbutamol"
    ]
    assert [a["medicamento"] for a in receta_respuesta.data["advertencias_alergia"]] == [
        "Paracetamol"
    ]
    assert Receta.all_objects.filter(pk=receta_id, consulta_id=consulta_id).exists()
    assert MedicamentoRecetado.all_objects.filter(receta_id=receta_id).count() == 2

    # S2-11: un segundo registro controlado demuestra el orden cronológico.
    consulta = Consulta.all_objects.get(pk=consulta_id)
    Consulta.all_objects.filter(pk=consulta_id).update(
        fecha=_aware(FECHA_ATENCION, time(9))
    )
    anterior = Consulta.all_objects.create(
        clinica=clinica_configurada,
        cita=None,
        medico=medico,
        paciente=paciente,
        fecha=_aware(date(2026, 11, 15), time(10)),
        motivo="Consulta anterior auxiliar",
        observacion="Registro auxiliar para ordenamiento",
        diagnostico="Control previo",
    )
    conteos_antes = (
        Consulta.all_objects.count(),
        Receta.all_objects.count(),
        MedicamentoRecetado.all_objects.count(),
    )
    historial = medico_cliente.get(
        f"/api/v1/pacientes/{paciente_id}/historial-consultas/",
        {"ordering": "-fecha"},
    )
    assert historial.status_code == 200, historial.data
    assert [item["id"] for item in historial.data["results"]] == [
        consulta.pk, anterior.pk
    ]
    principal = historial.data["results"][0]
    assert principal["cita"]["id"] == cita_id
    assert principal["diagnostico"] == "Asma controlada"
    assert principal["recetas"][0]["id"] == receta_id
    assert len(principal["recetas"][0]["medicamentos"]) == 2
    assert conteos_antes == (
        Consulta.all_objects.count(),
        Receta.all_objects.count(),
        MedicamentoRecetado.all_objects.count(),
    )

    # S2-12: vinculación idempotente y portal exclusivamente propio.
    vinculacion_url = f"/api/v1/pacientes/{paciente_id}/vincular-usuario/"
    payload_vinculacion = {"usuario_id": usuario_paciente_a.pk}
    vinculacion = admin.post(vinculacion_url, payload_vinculacion, format="json")
    repetida = admin.post(vinculacion_url, payload_vinculacion, format="json")
    esperado = {
        "codigo": "usuario_vinculado",
        "mensaje": "Usuario vinculado correctamente.",
        "paciente_id": paciente_id,
        "usuario_id": usuario_paciente_a.pk,
    }
    assert vinculacion.status_code == repetida.status_code == 200
    assert vinculacion.data == repetida.data == esperado

    portal = cliente_autenticado(usuario_paciente_a)
    informacion = portal.get("/api/v1/portal-paciente/mi-informacion/")
    historia_portal = portal.get("/api/v1/portal-paciente/mi-historia/")
    citas_portal = portal.get("/api/v1/portal-paciente/mis-citas/")
    consultas_portal = portal.get("/api/v1/portal-paciente/mis-consultas/")
    receta_portal = portal.get(f"/api/v1/portal-paciente/mis-recetas/{receta_id}/")
    assert informacion.status_code == historia_portal.status_code == 200
    assert citas_portal.status_code == consultas_portal.status_code == receta_portal.status_code == 200
    assert set(informacion.data) == {
        "id", "ci", "nombre", "apellido", "sexo", "fecha_nacimiento",
        "telefono", "email", "estado",
    }
    assert informacion.data["id"] == paciente_id
    assert historia_portal.data["observaciones_generales"] == "Antecedentes revisados en la demostración."
    assert historia_portal.data["enfermedades"][0]["nombre"] == "Asma"
    assert historia_portal.data["alergias"][0]["nombre"] == "Paracetamol"
    assert [item["id"] for item in citas_portal.data["results"]] == [cita_id]
    ids_consultas = [item["id"] for item in consultas_portal.data["results"]]
    assert ids_consultas == [consulta_id, anterior.pk]
    assert consultas_portal.data["results"][0]["observacion"] == "Paciente estable durante la atención."
    assert receta_portal.data["id"] == receta_id
    assert [m["nombre_medicamento"] for m in receta_portal.data["medicamentos"]] == [
        "Paracetamol", "Salbutamol"
    ]
    prohibido = portal.get(
        "/api/v1/portal-paciente/mis-consultas/", {"paciente_id": anterior.pk}
    )
    assert prohibido.status_code == 400
    assert prohibido.data["codigo"] == "datos_invalidos"
    assert portal.post("/api/v1/portal-paciente/mi-informacion/", {}, format="json").status_code == 405
