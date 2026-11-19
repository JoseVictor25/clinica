"""Pruebas API de estudios médicos (subida, bloqueo por consulta, descarga y lectura)."""

from datetime import date, time
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.atencion.models import (
    Cita,
    Consulta,
    EstadoCita,
    EstadoEstudio,
    FormatoEstudio,
    TipoEstudio,
)
from apps.pacientes.models import HistoriaClinica
from tests.api.helpers import cliente_autenticado, crear_personal_medico


FECHA = date(2026, 11, 16)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("nombre_archivo", "formato_esperado", "tipo_estudio"),
    [
        ("torax_frontal.dcm", FormatoEstudio.DICOM, TipoEstudio.TOMOGRAFIA),
        ("radiografia.png", FormatoEstudio.IMAGEN, TipoEstudio.RADIOGRAFIA),
        ("laboratorio.pdf", FormatoEstudio.PDF, TipoEstudio.LABORATORIO),
    ],
)
def test_paciente_sube_estudios_y_vincula_historia_clinica(
    clinica_configurada,
    suscripcion_amplia,
    medico_a,
    usuario_paciente_a,
    paciente_a,
    nombre_archivo,
    formato_esperado,
    tipo_estudio,
):
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="CI-EST-001", colegiatura="COL-EST-001"
    )
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])
    historia = HistoriaClinica.all_objects.create(paciente=paciente_a)

    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(9, 0),
        estado=EstadoCita.CONFIRMADA,
        motivo="Revisión de estudio",
    )

    archivo = SimpleUploadedFile(nombre_archivo, b"contenido-prueba")
    with patch(
        "apps.atencion.estudios_services._subir_a_supabase",
        return_value=f"https://example.supabase.co/storage/v1/object/public/estudios-medicos/{nombre_archivo}",
    ) as mock_subir:
        resp = cliente_autenticado(usuario_paciente_a).post(
            "/api/v1/estudios-medicos/",
            {
                "tipo_estudio": tipo_estudio,
                "cita_id": cita.pk,
                "archivo": archivo,
            },
            format="multipart",
        )

    assert resp.status_code == 201
    assert mock_subir.call_count == 1
    assert resp.data["formato"] == formato_esperado
    assert resp.data["estado"] == EstadoEstudio.PENDIENTE_REVISION
    assert resp.data["historia_clinica_id"] == historia.pk
    assert resp.data["cita_id"] == cita.pk
    assert resp.data["puede_modificar"] is True


@pytest.mark.django_db
def test_no_permite_subir_ni_modificar_si_cita_tiene_consulta(
    clinica_configurada, suscripcion_amplia, medico_a, usuario_paciente_a, paciente_a
):
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="CI-EST-002", colegiatura="COL-EST-002"
    )
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])

    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(10, 0),
        estado=EstadoCita.CONFIRMADA,
        motivo="Control",
    )

    with patch(
        "apps.atencion.estudios_services._subir_a_supabase",
        return_value="https://example.supabase.co/storage/v1/object/public/estudios-medicos/a.pdf",
    ):
        creado = cliente_autenticado(usuario_paciente_a).post(
            "/api/v1/estudios-medicos/",
            {
                "tipo_estudio": TipoEstudio.LABORATORIO,
                "cita_id": cita.pk,
                "archivo": SimpleUploadedFile("a.pdf", b"%PDF-1.4"),
            },
            format="multipart",
        )
    assert creado.status_code == 201
    estudio_id = creado.data["id"]

    Consulta.all_objects.create(
        clinica=clinica_configurada,
        cita=cita,
        medico=medico,
        paciente=paciente_a,
        motivo="Control",
        observacion="Todo bien",
        diagnostico="Sano",
    )
    cita.estado = EstadoCita.ATENDIDA
    cita.save(update_fields=["estado"])

    resp_nuevo = cliente_autenticado(usuario_paciente_a).post(
        "/api/v1/estudios-medicos/",
        {
            "tipo_estudio": TipoEstudio.RADIOGRAFIA,
            "cita_id": cita.pk,
            "archivo": SimpleUploadedFile("b.png", b"png-bytes"),
        },
        format="multipart",
    )
    assert resp_nuevo.status_code == 409

    resp_patch = cliente_autenticado(usuario_paciente_a).patch(
        f"/api/v1/estudios-medicos/{estudio_id}/",
        {"tipo_estudio": TipoEstudio.ECOGRAFIA},
        format="multipart",
    )
    assert resp_patch.status_code == 409

    resp_delete = cliente_autenticado(usuario_paciente_a).delete(
        f"/api/v1/estudios-medicos/{estudio_id}/"
    )
    assert resp_delete.status_code == 409


@pytest.mark.django_db
def test_medico_lista_descarga_y_revisa_estudio_de_cita(
    clinica_configurada, suscripcion_amplia, medico_a, usuario_paciente_a, paciente_a
):
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="CI-EST-003", colegiatura="COL-EST-003"
    )
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])

    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(11, 0),
        estado=EstadoCita.CONFIRMADA,
        motivo="Evaluar estudio",
    )

    with patch(
        "apps.atencion.estudios_services._subir_a_supabase",
        return_value="https://example.supabase.co/storage/v1/object/public/estudios-medicos/rx.jpg",
    ):
        creado = cliente_autenticado(usuario_paciente_a).post(
            "/api/v1/estudios-medicos/",
            {
                "tipo_estudio": TipoEstudio.RADIOGRAFIA,
                "cita_id": cita.pk,
                "archivo": SimpleUploadedFile("rx.jpg", b"jpeg-bytes"),
            },
            format="multipart",
        )
    estudio_id = creado.data["id"]

    lista = cliente_autenticado(medico_a).get("/api/v1/estudios-medicos/", {"cita_id": cita.pk})
    assert lista.status_code == 200
    assert lista.data["count"] == 1

    with patch(
        "apps.atencion.estudios_services._descargar_de_supabase",
        return_value=(b"jpeg-bytes", "image/jpeg"),
    ):
        archivo_resp = cliente_autenticado(medico_a).get(
            f"/api/v1/estudios-medicos/{estudio_id}/archivo/"
        )
    assert archivo_resp.status_code == 200
    assert archivo_resp.content == b"jpeg-bytes"

    revisar_resp = cliente_autenticado(medico_a).patch(
        f"/api/v1/estudios-medicos/{estudio_id}/revisar/",
        {"observacion_lectura": "Sin lesiones aparentes."},
        format="json",
    )
    assert revisar_resp.status_code == 200
    assert revisar_resp.data["estado"] == EstadoEstudio.REVISADO
    assert revisar_resp.data["observacion_lectura"] == "Sin lesiones aparentes."
    assert revisar_resp.data["medico_id"] == medico.pk


@pytest.mark.django_db
def test_rechaza_extension_no_soportada(
    clinica_configurada, suscripcion_amplia, usuario_paciente_a, paciente_a
):
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])

    resp = cliente_autenticado(usuario_paciente_a).post(
        "/api/v1/estudios-medicos/",
        {
            "tipo_estudio": TipoEstudio.LABORATORIO,
            "archivo": SimpleUploadedFile("malicioso.exe", b"MZ"),
        },
        format="multipart",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_crear_consulta_vincula_estudios_de_la_cita(
    clinica_configurada, suscripcion_amplia, medico_a, usuario_paciente_a, paciente_a
):
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="CI-EST-004", colegiatura="COL-EST-004"
    )
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])
    HistoriaClinica.all_objects.create(paciente=paciente_a)

    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(12, 0),
        estado=EstadoCita.CONFIRMADA,
        motivo="Teleconsulta con estudio previo",
    )

    with patch(
        "apps.atencion.estudios_services._subir_a_supabase",
        return_value="https://example.supabase.co/storage/v1/object/public/estudios-medicos/tc.dcm",
    ):
        creado = cliente_autenticado(usuario_paciente_a).post(
            "/api/v1/estudios-medicos/",
            {
                "tipo_estudio": TipoEstudio.TOMOGRAFIA,
                "cita_id": cita.pk,
                "archivo": SimpleUploadedFile("tc.dcm", b"DICM"),
            },
            format="multipart",
        )
    assert creado.status_code == 201
    estudio_id = creado.data["id"]
    assert creado.data["consulta_id"] is None

    consulta_resp = cliente_autenticado(medico_a).post(
        "/api/v1/consultas/",
        {
            "cita_id": cita.pk,
            "motivo": "Teleconsulta con estudio previo",
            "observacion": "Se evalúa tomografía durante la llamada.",
            "diagnostico": "Normal",
        },
        format="json",
    )
    assert consulta_resp.status_code == 201
    consulta_id = consulta_resp.data["id"]

    estudio_resp = cliente_autenticado(medico_a).get(f"/api/v1/estudios-medicos/{estudio_id}/")
    assert estudio_resp.status_code == 200
    assert estudio_resp.data["consulta_id"] == consulta_id
    assert estudio_resp.data["puede_modificar"] is False


@pytest.mark.django_db
def test_admin_clinica_agrega_y_elimina_estudios_de_cita(
    clinica_configurada, suscripcion_amplia, admin_a, medico_citas, paciente_a
):
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico_citas,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(13, 0),
        estado=EstadoCita.PROGRAMADA,
        motivo="Cita con estudios cargados por administración",
    )

    with patch(
        "apps.atencion.estudios_services._subir_a_supabase",
        return_value="https://example.supabase.co/storage/v1/object/public/estudios-medicos/eco.png",
    ):
        creado = cliente_autenticado(admin_a).post(
            "/api/v1/estudios-medicos/",
            {
                "tipo_estudio": TipoEstudio.ECOGRAFIA,
                "cita_id": cita.pk,
                "archivo": SimpleUploadedFile("eco.png", b"png-bytes"),
            },
            format="multipart",
        )
    assert creado.status_code == 201
    estudio_id = creado.data["id"]
    assert creado.data["paciente_id"] == paciente_a.pk
    assert creado.data["cita_id"] == cita.pk

    with patch("apps.atencion.estudios_services._eliminar_de_supabase") as mock_eliminar:
        eliminado = cliente_autenticado(admin_a).delete(
            f"/api/v1/estudios-medicos/{estudio_id}/"
        )
    assert eliminado.status_code == 204
    assert mock_eliminar.call_count == 1
