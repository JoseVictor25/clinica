from types import SimpleNamespace
from unittest.mock import Mock, patch
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.atencion.models import Cita
from apps.notificaciones.models import DispositivoPush, Notificacion
from apps.notificaciones.services import (
    enviar_push_usuario,
    enviar_recordatorios_citas_proximas,
    programar_notificacion_cita,
)
from tests.api.helpers import cliente_autenticado

URL = "/api/v1/notificaciones/dispositivos/"
INBOX_URL = "/api/v1/notificaciones/"


@pytest.mark.django_db
def test_registra_actualiza_y_elimina_dispositivo(admin_a, suscripcion_amplia):
    cliente = cliente_autenticado(admin_a)
    datos = {"token": "fid-prueba-001", "plataforma": "ANDROID"}

    primera = cliente.post(URL, datos, format="json")
    repetida = cliente.post(
        URL,
        {**datos, "plataforma": "IOS"},
        format="json",
    )

    assert primera.status_code == 200
    assert repetida.status_code == 200
    dispositivo = DispositivoPush.all_objects.get(token=datos["token"])
    assert dispositivo.usuario_id == admin_a.pk
    assert dispositivo.plataforma == "IOS"
    assert DispositivoPush.all_objects.filter(usuario=admin_a).count() == 1

    eliminado = cliente.delete(URL, data={**datos, "plataforma": "IOS"}, format="json")
    assert eliminado.status_code == 204
    assert not DispositivoPush.all_objects.filter(token=datos["token"]).exists()


@pytest.mark.django_db
def test_token_no_se_puede_asignar_a_otra_cuenta(
    admin_a, recepcionista_a, suscripcion_amplia
):
    token = "fid-compartido"
    cliente_autenticado(admin_a).post(
        URL,
        {"token": token, "plataforma": "ANDROID"},
        format="json",
    )

    respuesta = cliente_autenticado(recepcionista_a).post(
        URL,
        {"token": token, "plataforma": "ANDROID"},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "dispositivo_vinculado"
    assert DispositivoPush.all_objects.get(token=token).usuario_id == admin_a.pk


@pytest.mark.django_db
def test_envia_a_fids_registrados_sin_incluir_datos_clinicos(
    admin_a, suscripcion_amplia
):
    DispositivoPush.all_objects.create(
        usuario=admin_a,
        token="firebase-installation-id",
        plataforma="ANDROID",
    )
    messaging = Mock()
    messaging.send_each_for_multicast.return_value = SimpleNamespace(
        success_count=1,
        responses=[SimpleNamespace(success=True, exception=None)],
    )

    with patch(
        "apps.notificaciones.services._firebase_messaging",
        return_value=(messaging, object()),
    ):
        enviados = enviar_push_usuario(
            usuario_id=admin_a.pk,
            titulo="Actualización de cita",
            cuerpo="Abre la app para revisar tu cita.",
            datos={"tipo": "cita", "cita_id": 7},
        )

    assert enviados == 1
    mensaje = messaging.MulticastMessage.call_args.kwargs
    assert mensaje["fids"] == ["firebase-installation-id"]
    assert mensaje["data"] == {"tipo": "cita", "cita_id": "7"}
    assert not any("diagnostico" in clave for clave in mensaje["data"])


@pytest.mark.django_db
def test_bandeja_lista_solo_notificaciones_del_usuario_y_marca_leidas(
    admin_a, recepcionista_a, suscripcion_amplia
):
    propia = Notificacion.all_objects.create(
        usuario=admin_a,
        titulo="Actualización de cita",
        cuerpo="Tu cita médica fue confirmada.",
        datos={"tipo": "cita", "evento": "confirmada"},
    )
    Notificacion.all_objects.create(
        usuario=recepcionista_a,
        titulo="Notificación privada",
        cuerpo="No debe aparecer para otra cuenta.",
    )
    cliente = cliente_autenticado(admin_a)

    respuesta = cliente.get(INBOX_URL)

    assert respuesta.status_code == 200
    assert respuesta.data["no_leidas"] == 1
    assert len(respuesta.data["resultados"]) == 1
    assert respuesta.data["resultados"][0]["id"] == propia.pk
    assert respuesta.data["resultados"][0]["leida"] is False

    marcada = cliente.post(f"{INBOX_URL}{propia.pk}/leer/", {}, format="json")
    assert marcada.status_code == 200
    propia.refresh_from_db()
    assert propia.leida_en is not None
    assert cliente.get(INBOX_URL).data["no_leidas"] == 0


@pytest.mark.django_db
def test_bandeja_marca_todas_como_leidas(admin_a, suscripcion_amplia):
    Notificacion.all_objects.create(
        usuario=admin_a,
        titulo="Cita registrada",
        cuerpo="Revisa la app.",
    )
    cliente = cliente_autenticado(admin_a)

    respuesta = cliente.post(INBOX_URL, {}, format="json")

    assert respuesta.status_code == 200
    assert respuesta.data["actualizadas"] == 1
    assert cliente.get(INBOX_URL).data["no_leidas"] == 0


@pytest.mark.django_db
def test_evento_de_cita_crea_notificacion_persistente_para_medico_y_paciente(
    clinica_configurada,
    medico_a,
    usuario_paciente_a,
    medico_citas,
    paciente_a,
):
    medico_citas.personal.usuario = medico_a
    medico_citas.personal.save(update_fields=("usuario",))
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=("usuario",))
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico_citas,
        paciente=paciente_a,
        fecha="2026-11-23",
        hora="08:00",
        motivo="Control",
    )

    with (
        patch("apps.notificaciones.services.enviar_push_usuario") as enviar,
        patch(
            "apps.notificaciones.services.transaction.on_commit",
            side_effect=lambda callback: callback(),
        ),
    ):
        programar_notificacion_cita(cita_id=cita.pk, evento="programada")

    assert Notificacion.all_objects.filter(
        usuario_id__in=(medico_a.pk, usuario_paciente_a.pk),
        datos__cita_id=cita.pk,
        datos__evento="programada",
    ).count() == 2
    assert enviar.call_count == 2


@pytest.mark.django_db
def test_recordatorio_dos_horas_se_guarda_y_no_se_duplica(
    clinica_configurada,
    medico_citas,
    usuario_paciente_a,
    paciente_a,
):
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=("usuario",))
    ahora = timezone.localtime().replace(second=0, microsecond=0)
    momento_cita = ahora + timedelta(hours=1, minutes=59)
    cita = Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico_citas,
        paciente=paciente_a,
        fecha=momento_cita.date(),
        hora=momento_cita.time(),
        motivo="Control",
    )

    with patch("apps.notificaciones.services.enviar_push_usuario") as enviar:
        primera_ejecucion = enviar_recordatorios_citas_proximas(ahora=ahora)
        segunda_ejecucion = enviar_recordatorios_citas_proximas(ahora=ahora)

    recordatorios = Notificacion.all_objects.filter(
        usuario=usuario_paciente_a,
        datos__tipo="recordatorio_cita_2h",
        datos__cita_id=cita.pk,
    )
    assert primera_ejecucion == 1
    assert segunda_ejecucion == 0
    assert recordatorios.count() == 1
    assert enviar.call_count == 1
