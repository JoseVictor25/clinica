from datetime import date, time

import pytest

from apps.atencion.models import Cita, Consulta, EstadoCita
from apps.pacientes.models import Paciente
from tests.api.helpers import cliente_autenticado, crear_personal_medico


@pytest.mark.django_db
def test_medico_solo_lista_pacientes_atendidos_o_con_cita_activa(
    medico_a, clinica_configurada, suscripcion_amplia
):
    _, medico = crear_personal_medico(clinica_configurada, medico_a)

    def crear_paciente(ci):
        return Paciente.all_objects.create(
            clinica=clinica_configurada,
            ci=ci,
            nombre="Paciente",
            apellido=ci,
            sexo="F",
            fecha_nacimiento=date(1990, 1, 1),
            telefono="70000000",
        )

    atendido = crear_paciente("ATENDIDO")
    proximo = crear_paciente("PROXIMO")
    cancelado = crear_paciente("CANCELADO")
    ajeno = crear_paciente("AJENO")

    Consulta.all_objects.create(
        clinica=clinica_configurada,
        medico=medico,
        paciente=atendido,
        motivo="Control",
        observacion="Evaluación",
        diagnostico="Estable",
    )
    for paciente, estado in (
        (proximo, EstadoCita.CONFIRMADA),
        (cancelado, EstadoCita.CANCELADA),
    ):
        Cita.all_objects.create(
            clinica=clinica_configurada,
            medico=medico,
            paciente=paciente,
            fecha=date(2026, 11, 25),
            hora=time(9, 0),
            estado=estado,
            motivo="Consulta",
        )

    respuesta = cliente_autenticado(medico_a).get("/api/v1/pacientes/")

    assert respuesta.status_code == 200
    ids = {paciente["id"] for paciente in respuesta.data["results"]}
    assert ids == {atendido.pk, proximo.pk}
    assert cancelado.pk not in ids
    assert ajeno.pk not in ids


@pytest.mark.django_db
def test_medico_no_puede_abrir_ficha_ni_historia_de_paciente_ajeno(
    medico_a, clinica_configurada, suscripcion_amplia, paciente_a
):
    crear_personal_medico(clinica_configurada, medico_a)
    cliente = cliente_autenticado(medico_a)

    assert cliente.get(f"/api/v1/pacientes/{paciente_a.pk}/").status_code == 404
    assert (
        cliente.get(
            f"/api/v1/pacientes/{paciente_a.pk}/historial-consultas/"
        ).status_code
        == 404
    )
