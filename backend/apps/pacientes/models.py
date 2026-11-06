"""Pacientes, historia clínica, enfermedades y alergias."""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.managers import TenantChildModel, TenantModel


class Sexo(models.TextChoices):
    MASCULINO = "M", "Masculino"
    FEMENINO = "F", "Femenino"
    OTRO = "OTRO", "Otro"


class GrupoSanguineo(models.TextChoices):
    A_POSITIVO = "A+", "A+"
    A_NEGATIVO = "A-", "A-"
    B_POSITIVO = "B+", "B+"
    B_NEGATIVO = "B-", "B-"
    AB_POSITIVO = "AB+", "AB+"
    AB_NEGATIVO = "AB-", "AB-"
    O_POSITIVO = "O+", "O+"
    O_NEGATIVO = "O-", "O-"
    DESCONOCIDO = "DESC", "Desconocido"


class Paciente(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="pacientes",
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="paciente",
    )
    ci = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    sexo = models.CharField(max_length=10, choices=Sexo.choices)
    fecha_nacimiento = models.DateField()
    telefono = models.CharField(max_length=30)
    email = models.EmailField(max_length=254, blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"
        ordering = ["apellido", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "ci"],
                name="uniq_paciente_ci_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "apellido", "nombre"],
                name="paciente_clinica_nombre_idx",
            ),
            models.Index(
                fields=["fecha_nacimiento"],
                name="paciente_fecha_nac_idx",
            ),
            models.Index(
                fields=["clinica", "estado"],
                name="paciente_clinica_estado_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.usuario_id
            and self.clinica_id
            and self.usuario.clinica_id != self.clinica_id
        ):
            raise ValidationError(
                "El usuario vinculado debe pertenecer a la misma clínica."
            )
        if self.fecha_nacimiento and self.fecha_nacimiento > timezone.localdate():
            raise ValidationError(
                "La fecha de nacimiento no puede ser futura."
            )

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.ci})"


class HistoriaClinica(TenantChildModel):
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.PROTECT,
        related_name="historia",
    )
    fecha_apertura = models.DateField(default=date.today)
    grupo_sanguineo = models.CharField(
        max_length=4,
        choices=GrupoSanguineo.choices,
        default=GrupoSanguineo.DESCONOCIDO,
    )
    observaciones_generales = models.TextField(blank=True)
    estado = models.BooleanField(default=True)
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True)

    tenant_lookup = "paciente__clinica"

    class Meta:
        verbose_name = "historia clínica"
        verbose_name_plural = "historias clínicas"
        ordering = ["-fecha_apertura"]
        indexes = [
            models.Index(
                fields=["fecha_apertura"],
                name="historia_fecha_apertura_idx",
            ),
        ]

    def __str__(self):
        return f"Historia de {self.paciente}"


class TipoEnfermedad(models.TextChoices):
    CRONICA = "CRONICA", "Crónica"
    AGUDA = "AGUDA", "Aguda"
    HEREDITARIA = "HEREDITARIA", "Hereditaria"
    INFECCIOSA = "INFECCIOSA", "Infecciosa"
    OTRA = "OTRA", "Otra"


class Severidad(models.TextChoices):
    LEVE = "LEVE", "Leve"
    MODERADA = "MODERADA", "Moderada"
    GRAVE = "GRAVE", "Grave"


class Enfermedad(TenantChildModel):
    historia = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.CASCADE,
        related_name="enfermedades",
    )
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(
        max_length=30,
        choices=TipoEnfermedad.choices,
        default=TipoEnfermedad.OTRA,
    )
    severidad = models.CharField(
        max_length=20,
        choices=Severidad.choices,
        default=Severidad.LEVE,
    )
    fecha_deteccion = models.DateField()

    tenant_lookup = "historia__paciente__clinica"

    class Meta:
        verbose_name = "enfermedad"
        verbose_name_plural = "enfermedades"
        ordering = ["-fecha_deteccion"]
        indexes = [
            models.Index(
                fields=["historia", "fecha_deteccion"],
                name="enfermedad_hist_fecha_idx",
            ),
            models.Index(
                fields=["nombre"],
                name="enfermedad_nombre_idx",
            ),
        ]

    def __str__(self):
        return self.nombre


class TipoAlergia(models.TextChoices):
    MEDICAMENTO = "MEDICAMENTO", "Medicamento"
    ALIMENTO = "ALIMENTO", "Alimento"
    AMBIENTAL = "AMBIENTAL", "Ambiental"
    OTRA = "OTRA", "Otra"


class Alergia(TenantChildModel):
    historia = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.CASCADE,
        related_name="alergias",
    )
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(
        max_length=30,
        choices=TipoAlergia.choices,
        default=TipoAlergia.OTRA,
    )
    severidad = models.CharField(
        max_length=20,
        choices=Severidad.choices,
        default=Severidad.LEVE,
    )
    descripcion = models.TextField(blank=True)

    tenant_lookup = "historia__paciente__clinica"

    class Meta:
        verbose_name = "alergia"
        verbose_name_plural = "alergias"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["historia", "nombre"],
                name="uniq_alergia_por_historia",
            ),
        ]

    def __str__(self):
        return self.nombre
