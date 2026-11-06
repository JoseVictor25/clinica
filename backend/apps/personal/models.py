"""Personal de la clínica, especialidades, médicos y horarios."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.core.managers import TenantChildModel, TenantModel


class CargoPersonal(models.TextChoices):
    MEDICO = "MEDICO", "Médico"
    ENFERMERIA = "ENFERMERIA", "Enfermería"
    RECEPCION = "RECEPCION", "Recepción"
    CONDUCTOR = "CONDUCTOR", "Conductor"
    OTRO = "OTRO", "Otro"


class Personal(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="personal",
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="personal",
    )
    ci = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=30)
    cargo = models.CharField(
        max_length=80,
        choices=CargoPersonal.choices,
        default=CargoPersonal.OTRO,
    )
    fecha_ingreso = models.DateField()
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "personal"
        verbose_name_plural = "personal"
        ordering = ["apellido", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "ci"],
                name="uniq_personal_ci_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "apellido", "nombre"],
                name="personal_clinica_nombre_idx",
            ),
            models.Index(
                fields=["clinica", "cargo"],
                name="personal_clinica_cargo_idx",
            ),
            models.Index(
                fields=["clinica", "estado"],
                name="personal_clinica_estado_idx",
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

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class Especialidad(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="especialidades",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "especialidad"
        verbose_name_plural = "especialidades"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "nombre"],
                name="uniq_especialidad_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "estado"],
                name="especialidad_clinica_idx",
            ),
        ]

    def __str__(self):
        return self.nombre


class Medico(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="medicos",
    )
    personal = models.OneToOneField(
        Personal,
        on_delete=models.CASCADE,
        related_name="medico",
    )
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.PROTECT,
        related_name="medicos",
    )
    numero_colegiatura = models.CharField(max_length=30, unique=True)
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "médico"
        verbose_name_plural = "médicos"
        ordering = ["personal__apellido", "personal__nombre"]
        indexes = [
            models.Index(
                fields=["clinica", "estado"],
                name="medico_clinica_estado_idx",
            ),
            models.Index(
                fields=["especialidad"],
                name="medico_especialidad_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.personal_id and self.clinica_id:
            if self.personal.clinica_id != self.clinica_id:
                raise ValidationError(
                    "El médico y su registro de personal deben pertenecer a la misma clínica."
                )
        if self.especialidad_id and self.clinica_id:
            if self.especialidad.clinica_id != self.clinica_id:
                raise ValidationError(
                    "La especialidad debe pertenecer a la misma clínica del médico."
                )

    def __str__(self):
        return f"{self.personal} - {self.numero_colegiatura}"


class DiaSemana(models.IntegerChoices):
    LUNES = 0, "Lunes"
    MARTES = 1, "Martes"
    MIERCOLES = 2, "Miércoles"
    JUEVES = 3, "Jueves"
    VIERNES = 4, "Viernes"
    SABADO = 5, "Sábado"
    DOMINGO = 6, "Domingo"


class HorarioAtencion(TenantChildModel):
    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name="horarios",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    tenant_lookup = "medico__clinica"

    class Meta:
        verbose_name = "horario de atención"
        verbose_name_plural = "horarios de atención"
        ordering = ["medico", "dia_semana", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_inicio__lt=F("hora_fin")),
                name="horario_horas_validas",
            ),
            models.UniqueConstraint(
                fields=["medico", "dia_semana", "hora_inicio", "hora_fin"],
                name="uniq_horario_exacto",
            ),
        ]
        indexes = [
            models.Index(
                fields=["medico", "dia_semana"],
                name="horario_medico_dia_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.hora_inicio
            and self.hora_fin
            and self.hora_inicio >= self.hora_fin
        ):
            raise ValidationError(
                "La hora de inicio debe ser anterior a la hora de fin."
            )

    def __str__(self):
        return (
            f"{self.medico} - {self.get_dia_semana_display()} "
            f"{self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"
        )
