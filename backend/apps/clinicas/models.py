"""Entidades del núcleo SaaS: clínica, plan y suscripción."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.core.managers import TenantModel


class Clinica(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(max_length=254)
    nit = models.CharField(max_length=20, unique=True)
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "clínica"
        verbose_name_plural = "clínicas"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"], name="clinica_nombre_idx"),
            models.Index(fields=["estado"], name="clinica_estado_idx"),
        ]

    def __str__(self):
        return self.nombre


class PlanSuscripcion(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    max_usuarios = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "plan de suscripción"
        verbose_name_plural = "planes de suscripción"
        ordering = ["precio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(precio__gte=0),
                name="plan_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(max_usuarios__gt=0),
                name="plan_max_usuarios_positivo",
            ),
        ]
        indexes = [
            models.Index(fields=["activo"], name="plan_activo_idx"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.max_usuarios} usuarios)"


class Suscripcion(TenantModel):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        VENCIDA = "VENCIDA", "Vencida"
        CANCELADA = "CANCELADA", "Cancelada"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"

    clinica = models.ForeignKey(
        Clinica,
        on_delete=models.PROTECT,
        related_name="suscripciones",
    )
    plan = models.ForeignKey(
        PlanSuscripcion,
        on_delete=models.PROTECT,
        related_name="suscripciones",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )

    class Meta:
        verbose_name = "suscripción"
        verbose_name_plural = "suscripciones"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin__gte=F("fecha_inicio")),
                name="suscripcion_fechas_validas",
            ),
            models.UniqueConstraint(
                fields=["clinica"],
                condition=Q(estado="ACTIVA"),
                name="uniq_susc_activa_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "estado"],
                name="susc_clinica_estado_idx",
            ),
            models.Index(
                fields=["clinica", "fecha_fin"],
                name="susc_clinica_fecha_fin_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )

    def __str__(self):
        return f"{self.clinica} - {self.plan} ({self.estado})"
