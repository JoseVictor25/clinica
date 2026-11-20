"""Registro de dispositivos y envío de mensajes mediante Firebase Cloud Messaging."""

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _firebase_messaging():
    if not settings.FCM_ENABLED:
        return None

    import firebase_admin
    from firebase_admin import credentials, messaging

    try:
        app = firebase_admin.get_app()
    except ValueError:
        ruta_credenciales = settings.FCM_SERVICE_ACCOUNT_FILE
        credencial = (
            credentials.Certificate(ruta_credenciales)
            if ruta_credenciales
            else credentials.ApplicationDefault()
        )
        app = firebase_admin.initialize_app(credencial)
    return messaging, app


def enviar_push_usuario(*, usuario_id, titulo, cuerpo, datos=None):
    """Envía un mensaje genérico a los dispositivos activos del usuario."""
    cliente = _firebase_messaging()
    if cliente is None:
        return 0

    from .models import DispositivoPush

    tokens = list(
        DispositivoPush.all_objects.filter(usuario_id=usuario_id)
        .values_list("token", flat=True)
    )
    if not tokens:
        return 0

    messaging_module, app = cliente
    enviados = 0
    for inicio in range(0, len(tokens), 500):
        lote = tokens[inicio : inicio + 500]
        mensaje = messaging_module.MulticastMessage(
            fids=lote,
            notification=messaging_module.Notification(title=titulo, body=cuerpo),
            data={str(clave): str(valor) for clave, valor in (datos or {}).items()},
        )
        try:
            respuesta = messaging_module.send_each_for_multicast(mensaje, app=app)
        except Exception:
            logger.exception("No se pudo enviar el lote de notificaciones push.")
            continue

        enviados += respuesta.success_count
        invalidos = []
        for token, resultado in zip(lote, respuesta.responses):
            if resultado.success:
                continue
            error = resultado.exception
            codigo = getattr(error, "code", "")
            if isinstance(error, messaging_module.UnregisteredError) or codigo in {
                "messaging/registration-token-not-registered",
                "messaging/invalid-registration-token",
            }:
                invalidos.append(token)
        if invalidos:
            DispositivoPush.all_objects.filter(token__in=invalidos).delete()
    return enviados


def programar_notificacion_cita(*, cita_id, evento):
    """Notifica paciente y médico al confirmar la transacción de la cita."""

    def enviar():
        from apps.atencion.models import Cita

        cita = (
            Cita.all_objects.select_related(
                "paciente__usuario",
                "medico__personal__usuario",
            )
            .filter(pk=cita_id)
            .first()
        )
        if cita is None:
            return

        destinatarios = {
            usuario_id
            for usuario_id in (
                cita.paciente.usuario_id,
                cita.medico.personal.usuario_id,
            )
            if usuario_id is not None
        }
        etiquetas = {
            "programada": "registrada",
            "confirmada": "confirmada",
            "cancelada": "cancelada",
            "reprogramada": "reprogramada",
        }
        estado = etiquetas.get(evento, "actualizada")
        for usuario_id in destinatarios:
            try:
                from .models import Notificacion

                titulo = "Actualización de cita"
                cuerpo = (
                    f"Tu cita médica fue {estado}. Abre la app para ver los detalles."
                )
                Notificacion.all_objects.create(
                    usuario_id=usuario_id,
                    titulo=titulo,
                    cuerpo=cuerpo,
                    datos={"tipo": "cita", "cita_id": cita.pk, "evento": evento},
                )
                enviar_push_usuario(
                    usuario_id=usuario_id,
                    titulo=titulo,
                    cuerpo=cuerpo,
                    datos={"tipo": "cita", "cita_id": cita.pk, "evento": evento},
                )
            except Exception:
                logger.exception("Falló el envío push de una actualización de cita.")

    transaction.on_commit(enviar)


def enviar_recordatorios_citas_proximas(*, ahora=None):
    """Envía una sola notificación al paciente cerca de dos horas antes."""
    from apps.atencion.models import Cita, EstadoCita
    from .models import Notificacion

    ahora = timezone.localtime(ahora or timezone.now())
    limite = ahora + timedelta(hours=2)
    tolerancia = timedelta(minutes=5)
    candidatas = (
        Cita.all_objects.filter(
            estado__in=(EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA),
            paciente__usuario__isnull=False,
            fecha__gte=ahora.date(),
            fecha__lte=limite.date(),
        )
        .select_related("paciente__usuario", "medico__personal__usuario")
        .order_by("fecha", "hora", "id")
    )

    enviadas = 0
    for cita in candidatas:
        momento = timezone.make_aware(
            datetime.combine(cita.fecha, cita.hora),
            timezone.get_current_timezone(),
        )
        restante = momento - ahora
        # Se ejecuta cada minuto; la ventana permite absorber pequeñas demoras.
        if restante <= timedelta(0) or restante > timedelta(hours=2):
            continue
        if restante < timedelta(hours=2) - tolerancia:
            continue

        momento_clave = momento.isoformat()
        usuario_id = cita.paciente.usuario_id
        ya_enviada = Notificacion.all_objects.filter(
            usuario_id=usuario_id,
            datos__tipo="recordatorio_cita_2h",
            datos__cita_id=cita.pk,
            datos__momento_cita=momento_clave,
        ).exists()
        if ya_enviada:
            continue

        datos = {
            "tipo": "recordatorio_cita_2h",
            "cita_id": cita.pk,
            "momento_cita": momento_clave,
        }
        Notificacion.all_objects.create(
            usuario_id=usuario_id,
            titulo="Recordatorio de cita médica",
            cuerpo=(
                "Tienes una cita médica en aproximadamente dos horas. "
                "Abre la app para consultar los detalles."
            ),
            datos=datos,
        )
        enviar_push_usuario(
            usuario_id=usuario_id,
            titulo="Recordatorio de cita médica",
            cuerpo=(
                "Tienes una cita médica en aproximadamente dos horas. "
                "Abre la app para consultar los detalles."
            ),
            datos=datos,
        )
        enviadas += 1
    return enviadas
