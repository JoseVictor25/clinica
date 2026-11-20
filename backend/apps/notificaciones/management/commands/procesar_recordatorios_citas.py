"""Proceso residente que envía recordatorios de citas próximas."""

import logging
import time

from django.core.management.base import BaseCommand

from apps.notificaciones.services import enviar_recordatorios_citas_proximas

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía recordatorios push a pacientes dos horas antes de sus citas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--intervalo",
            type=int,
            default=60,
            help="Segundos entre revisiones (mínimo 15).",
        )

    def handle(self, *args, **options):
        intervalo = max(15, options["intervalo"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Procesador de recordatorios activo; revisión cada {intervalo}s."
            )
        )
        while True:
            try:
                cantidad = enviar_recordatorios_citas_proximas()
                if cantidad:
                    self.stdout.write(
                        f"Recordatorios enviados: {cantidad}."
                    )
            except Exception:
                logger.exception("Falló el procesamiento de recordatorios.")
            time.sleep(intervalo)
