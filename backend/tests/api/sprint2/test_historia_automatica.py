"""Pruebas de S2-02: creación transaccional de la historia clínica."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.api_exceptions import Conflicto, DatosInvalidos
from apps.pacientes.models import (
    GrupoSanguineo,
    HistoriaClinica,
    Paciente,
)
from apps.pacientes.services import crear_paciente
from tests.api.helpers import cliente_autenticado

URL = "/api/v1/pacientes/"


def _datos(ci="S2-02-001"):
    return {
        "ci": ci,
        "nombre": "Historia",
        "apellido": "Automática",
        "sexo": "OTRO",
        "fecha_nacimiento": date(1992, 4, 10),
        "telefono": "70000002",
        "email": "historia@example.com",
        "estado": True,
    }


@pytest.mark.django_db
def test_servicio_crea_historia_con_valores_iniciales(clinica_configurada):
    paciente = crear_paciente(clinica_configurada, _datos())

    historia = HistoriaClinica.all_objects.get(paciente=paciente)
    assert historia.fecha_apertura == date.today()
    assert historia.grupo_sanguineo == GrupoSanguineo.DESCONOCIDO
    assert historia.observaciones_generales == ""
    assert historia.estado is True
    assert historia.paciente.clinica_id == clinica_configurada.pk


@pytest.mark.django_db
def test_api_crea_una_historia_y_no_expone_datos_clinicos(
    admin_a,
    suscripcion_amplia,
):
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        {**_datos(), "fecha_nacimiento": "1992-04-10"},
        format="json",
    )

    assert respuesta.status_code == 201
    assert HistoriaClinica.all_objects.filter(
        paciente_id=respuesta.data["id"]
    ).count() == 1
    assert not {
        "historia",
        "grupo_sanguineo",
        "observaciones_generales",
        "fecha_apertura",
    }.intersection(respuesta.data)


@pytest.mark.django_db
def test_historias_permanecen_aisladas_por_clinica(
    clinica_configurada,
    clinica_b,
):
    paciente_a = crear_paciente(clinica_configurada, _datos("TENANT-A"))
    paciente_b = crear_paciente(clinica_b, _datos("TENANT-B"))

    historia_a = HistoriaClinica.all_objects.get(paciente=paciente_a)
    historia_b = HistoriaClinica.all_objects.get(paciente=paciente_b)
    assert historia_a.paciente.clinica_id == clinica_configurada.pk
    assert historia_b.paciente.clinica_id == clinica_b.pk
    assert historia_a.pk != historia_b.pk


@pytest.mark.django_db
def test_ci_duplicada_no_crea_historia_adicional(clinica_configurada):
    crear_paciente(clinica_configurada, _datos("DUPLICADA"))

    with pytest.raises(Conflicto) as error:
        crear_paciente(clinica_configurada, _datos("DUPLICADA"))

    assert error.value.codigo == "ci_duplicada"
    assert Paciente.all_objects.filter(
        clinica=clinica_configurada,
        ci="DUPLICADA",
    ).count() == 1
    assert HistoriaClinica.all_objects.count() == 1


@pytest.mark.django_db
def test_restriccion_ci_sigue_resolviendo_carrera_como_conflicto(
    clinica_configurada,
):
    crear_paciente(clinica_configurada, _datos("CARRERA"))

    with patch("apps.pacientes.services._existe_ci", return_value=False):
        with pytest.raises(Conflicto) as error:
            crear_paciente(clinica_configurada, _datos("CARRERA"))

    assert error.value.codigo == "ci_duplicada"
    assert HistoriaClinica.all_objects.count() == 1


@pytest.mark.django_db
def test_fecha_futura_no_crea_paciente_ni_historia(clinica_configurada):
    datos = _datos("FUTURA")
    datos["fecha_nacimiento"] = timezone.localdate() + timedelta(days=1)

    with pytest.raises(DatosInvalidos) as error:
        crear_paciente(clinica_configurada, datos)

    assert error.value.codigo == "fecha_nacimiento_invalida"
    assert not Paciente.all_objects.filter(ci="FUTURA").exists()
    assert HistoriaClinica.all_objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_fallo_de_historia_revierte_paciente_y_no_es_ci_duplicada(
    clinica_configurada,
):
    with patch.object(
        HistoriaClinica.all_objects,
        "create",
        side_effect=RuntimeError("fallo técnico simulado"),
    ):
        with pytest.raises(RuntimeError) as error:
            crear_paciente(clinica_configurada, _datos("ROLLBACK"))

    assert not isinstance(error.value, Conflicto)
    assert not Paciente.all_objects.filter(ci="ROLLBACK").exists()
    assert HistoriaClinica.all_objects.count() == 0


@pytest.mark.django_db
def test_editar_reactivar_y_desactivar_conserva_la_misma_historia(
    admin_a,
    suscripcion_amplia,
):
    paciente = crear_paciente(admin_a.clinica, _datos("CICLO"))
    historia_id = HistoriaClinica.all_objects.get(paciente=paciente).pk
    cliente = cliente_autenticado(admin_a)

    assert cliente.patch(
        f"{URL}{paciente.pk}/",
        {"nombre": "Editado"},
        format="json",
    ).status_code == 200
    assert cliente.delete(f"{URL}{paciente.pk}/").status_code == 204
    assert cliente.patch(
        f"{URL}{paciente.pk}/",
        {"estado": True},
        format="json",
    ).status_code == 200
    assert cliente.patch(
        f"{URL}{paciente.pk}/",
        {"estado": True},
        format="json",
    ).status_code == 200

    historias = HistoriaClinica.all_objects.filter(paciente=paciente)
    assert historias.count() == 1
    assert historias.get().pk == historia_id
    assert historias.get().estado is True


@pytest.mark.django_db
def test_relacion_uno_a_uno_impide_dos_historias(clinica_configurada):
    paciente = crear_paciente(clinica_configurada, _datos("UNO-A-UNO"))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            HistoriaClinica.all_objects.create(paciente=paciente)

    assert HistoriaClinica.all_objects.filter(paciente=paciente).count() == 1


@pytest.mark.django_db
def test_suscripcion_vencida_no_crea_paciente_ni_historia(
    admin_a,
):
    respuesta = cliente_autenticado(admin_a).post(
        URL,
        {**_datos("SIN-SUSCRIPCION"), "fecha_nacimiento": "1992-04-10"},
        format="json",
    )

    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "suscripcion_vencida"
    assert not Paciente.all_objects.filter(ci="SIN-SUSCRIPCION").exists()
    assert HistoriaClinica.all_objects.count() == 0


@pytest.mark.django_db
def test_openapi_documenta_creacion_automatica(cliente):
    respuesta = cliente.get("/api/schema/")
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "crea automáticamente su historia clínica" in contenido
    assert "única transacción" in contenido
