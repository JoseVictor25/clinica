"""Ambulancias, equipamiento, licencias de conducir y traslados."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.managers import TenantChildModel, TenantModel


class TipoAmbulancia(models.TextChoices):
    BASICA = "BASICA", "Básica"
    MEDICALIZADA = "MEDICALIZADA", "Medicalizada"
    UCI_MOVIL = "UCI_MOVIL", "UCI móvil"
    OTRA = "OTRA", "Otra"


class EstadoAmbulancia(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    EN_TRASLADO = "EN_TRASLADO", "En traslado"
    MANTENIMIENTO = "MANTENIMIENTO", "En mantenimiento"
    INACTIVA = "INACTIVA", "Inactiva"


class Ambulancia(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="ambulancias",
    )
    matricula = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(
        max_length=30,
        choices=TipoAmbulancia.choices,
        default=TipoAmbulancia.BASICA,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoAmbulancia.choices,
        default=EstadoAmbulancia.DISPONIBLE,
    )
    capacidad = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "ambulancia"
        verbose_name_plural = "ambulancias"
        ordering = ["matricula"]
        constraints = [
            models.CheckConstraint(
                condition=Q(capacidad__gt=0),
                name="ambulancia_capacidad_positiva",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "estado"],
                name="ambulancia_clinica_estado_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.capacidad is not None and self.capacidad <= 0:
            raise ValidationError("La capacidad debe ser mayor que cero.")

    def __str__(self):
        return f"{self.matricula} ({self.get_tipo_display()})"


class Equipamiento(TenantChildModel):
    ambulancia = models.ForeignKey(
        Ambulancia,
        on_delete=models.CASCADE,
        related_name="equipamientos",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    tenant_lookup = "ambulancia__clinica"

    class Meta:
        verbose_name = "equipamiento"
        verbose_name_plural = "equipamientos"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["ambulancia", "nombre"],
                name="uniq_equipamiento_ambulancia",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.ambulancia}"


class LicenciaConducir(TenantChildModel):
    personal = models.OneToOneField(
        "personal.Personal",
        on_delete=models.CASCADE,
        related_name="licencia",
    )
    numero = models.CharField(max_length=30, unique=True)
    categoria = models.CharField(max_length=10)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    tenant_lookup = "personal__clinica"

    class Meta:
        verbose_name = "licencia de conducir"
        verbose_name_plural = "licencias de conducir"
        ordering = ["fecha_vencimiento"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_vencimiento__gt=models.F("fecha_emision")),
                name="licencia_fechas_validas",
            ),
        ]
        indexes = [
            models.Index(
                fields=["fecha_vencimiento"],
                name="licencia_vencimiento_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.fecha_emision
            and self.fecha_vencimiento
            and self.fecha_vencimiento <= self.fecha_emision
        ):
            raise ValidationError(
                "La fecha de vencimiento debe ser posterior a la fecha de emisión."
            )

    def __str__(self):
        return f"{self.numero} ({self.categoria})"


class TipoTraslado(models.TextChoices):
    EMERGENCIA = "EMERGENCIA", "Emergencia"
    PROGRAMADO = "PROGRAMADO", "Programado"
    TRASLADO_INTERNO = "TRASLADO_INTERNO", "Traslado interno"
    ALTA = "ALTA", "Alta"
    OTRO = "OTRO", "Otro"


class EstadoTraslado(models.TextChoices):
    PROGRAMADO = "PROGRAMADO", "Programado"
    EN_CURSO = "EN_CURSO", "En curso"
    COMPLETADO = "COMPLETADO", "Completado"
    CANCELADO = "CANCELADO", "Cancelado"


class Traslado(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="traslados",
    )
    ambulancia = models.ForeignKey(
        Ambulancia,
        on_delete=models.PROTECT,
        related_name="traslados",
    )
    conductor = models.ForeignKey(
        "personal.Personal",
        on_delete=models.PROTECT,
        related_name="traslados_conducidos",
    )
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.PROTECT,
        related_name="traslados",
    )
    motivo = models.CharField(max_length=255)
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField(null=True, blank=True)
    tipo_traslado = models.CharField(
        max_length=30,
        choices=TipoTraslado.choices,
        default=TipoTraslado.PROGRAMADO,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoTraslado.choices,
        default=EstadoTraslado.PROGRAMADO,
    )
    observacion = models.TextField(blank=True)
    lugar_origen = models.CharField(max_length=255)
    lugar_destino = models.CharField(max_length=255)

    class Meta:
        verbose_name = "traslado"
        verbose_name_plural = "traslados"
        ordering = ["-fecha_salida"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_llegada__isnull=True)
                | Q(fecha_llegada__gte=models.F("fecha_salida")),
                name="traslado_fechas_validas",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "fecha_salida"],
                name="traslado_clinica_fecha_idx",
            ),
            models.Index(
                fields=["ambulancia", "fecha_salida"],
                name="traslado_ambulancia_fecha_idx",
            ),
            models.Index(
                fields=["conductor", "fecha_salida"],
                name="traslado_conductor_fecha_idx",
            ),
            models.Index(
                fields=["paciente", "fecha_salida"],
                name="traslado_paciente_fecha_idx",
            ),
            models.Index(fields=["estado"], name="traslado_estado_idx"),
        ]

    def clean(self):
        super().clean()
        if not self.clinica_id:
            return
        if self.ambulancia_id and self.ambulancia.clinica_id != self.clinica_id:
            raise ValidationError(
                "La ambulancia debe pertenecer a la misma clínica del traslado."
            )
        if self.conductor_id and self.conductor.clinica_id != self.clinica_id:
            raise ValidationError(
                "El conductor debe pertenecer a la misma clínica del traslado."
            )
        if self.paciente_id and self.paciente.clinica_id != self.clinica_id:
            raise ValidationError(
                "El paciente debe pertenecer a la misma clínica del traslado."
            )
        if (
            self.fecha_salida
            and self.fecha_llegada
            and self.fecha_llegada < self.fecha_salida
        ):
            raise ValidationError(
                "La fecha de llegada no puede ser anterior a la fecha de salida."
            )

    def __str__(self):
        return f"{self.fecha_salida:%Y-%m-%d} - {self.paciente} ({self.estado})"
