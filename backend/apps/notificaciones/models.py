from django.conf import settings
from django.db import models

from apps.core.managers import TenantChildModel


class PlataformaDispositivo(models.TextChoices):
    ANDROID = "ANDROID", "Android"
    IOS = "IOS", "iOS"
    WEB = "WEB", "Web"


class DispositivoPush(TenantChildModel):
    """Token FCM asociado a una cuenta y clínica."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dispositivos_push",
    )
    token = models.CharField(max_length=4096, unique=True)
    plataforma = models.CharField(
        max_length=10,
        choices=PlataformaDispositivo.choices,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    tenant_lookup = "usuario__clinica"

    class Meta:
        ordering = ("-actualizado_en",)
        indexes = [models.Index(fields=("usuario", "plataforma"))]

    def __str__(self):
        return f"Dispositivo push de {self.usuario_id} ({self.plataforma})"


class Notificacion(TenantChildModel):
    """Notificación persistente de una cuenta dentro de su clínica."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    titulo = models.CharField(max_length=120)
    cuerpo = models.CharField(max_length=500)
    datos = models.JSONField(default=dict, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    leida_en = models.DateTimeField(null=True, blank=True)

    tenant_lookup = "usuario__clinica"

    class Meta:
        ordering = ("-creada_en",)
        indexes = [models.Index(fields=("usuario", "leida_en", "creada_en"))]

    def __str__(self):
        return f"Notificación para {self.usuario_id}: {self.titulo}"
