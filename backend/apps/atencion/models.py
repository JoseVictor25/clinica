"""Citas, consultas, recetas y medicamentos recetados."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.managers import TenantChildModel, TenantModel


class EstadoCita(models.TextChoices):
    PROGRAMADA = "PROGRAMADA", "Programada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    ATENDIDA = "ATENDIDA", "Atendida"
    CANCELADA = "CANCELADA", "Cancelada"
    NO_ASISTIO = "NO_ASISTIO", "No asistió"


class Cita(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="citas",
    )
    medico = models.ForeignKey(
        "personal.Medico",
        on_delete=models.PROTECT,
        related_name="citas",
    )
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.PROTECT,
        related_name="citas",
    )
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoCita.choices,
        default=EstadoCita.PROGRAMADA,
    )
    motivo = models.CharField(max_length=255)

    class Meta:
        verbose_name = "cita"
        verbose_name_plural = "citas"
        ordering = ["fecha", "hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["medico", "fecha", "hora"],
                condition=~Q(estado__in=["CANCELADA", "NO_ASISTIO"]),
                name="uniq_cita_medico_activa",
            ),
            models.UniqueConstraint(
                fields=["paciente", "fecha", "hora"],
                condition=~Q(estado__in=["CANCELADA", "NO_ASISTIO"]),
                name="uniq_cita_paciente_activa",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "fecha"],
                name="cita_clinica_fecha_idx",
            ),
            models.Index(
                fields=["medico", "fecha"],
                name="cita_medico_fecha_idx",
            ),
            models.Index(
                fields=["paciente", "fecha"],
                name="cita_paciente_fecha_idx",
            ),
            models.Index(fields=["estado"], name="cita_estado_idx"),
        ]

    def clean(self):
        super().clean()
        if not self.clinica_id:
            return
        if self.medico_id and self.medico.clinica_id != self.clinica_id:
            raise ValidationError(
                "El médico debe pertenecer a la misma clínica de la cita."
            )
        if self.paciente_id and self.paciente.clinica_id != self.clinica_id:
            raise ValidationError(
                "El paciente debe pertenecer a la misma clínica de la cita."
            )

    def __str__(self):
        return f"{self.fecha} {self.hora} - {self.paciente} con {self.medico}"


class Consulta(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="consultas",
    )
    cita = models.OneToOneField(
        Cita,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="consulta",
    )
    medico = models.ForeignKey(
        "personal.Medico",
        on_delete=models.PROTECT,
        related_name="consultas",
    )
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.PROTECT,
        related_name="consultas",
    )
    fecha = models.DateTimeField(default=timezone.now)
    motivo = models.TextField()
    observacion = models.TextField()
    diagnostico = models.TextField()

    class Meta:
        verbose_name = "consulta"
        verbose_name_plural = "consultas"
        ordering = ["-fecha"]
        indexes = [
            models.Index(
                fields=["clinica", "fecha"],
                name="consulta_clinica_fecha_idx",
            ),
            models.Index(
                fields=["medico", "fecha"],
                name="consulta_medico_fecha_idx",
            ),
            models.Index(
                fields=["paciente", "fecha"],
                name="consulta_paciente_fecha_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.clinica_id:
            return
        if self.medico_id and self.medico.clinica_id != self.clinica_id:
            raise ValidationError(
                "El médico debe pertenecer a la misma clínica de la consulta."
            )
        if self.paciente_id and self.paciente.clinica_id != self.clinica_id:
            raise ValidationError(
                "El paciente debe pertenecer a la misma clínica de la consulta."
            )
        if self.cita_id:
            if self.cita.clinica_id != self.clinica_id:
                raise ValidationError(
                    "La cita debe pertenecer a la misma clínica de la consulta."
                )
            if self.cita.medico_id != self.medico_id:
                raise ValidationError(
                    "El médico de la consulta debe coincidir con el de la cita."
                )
            if self.cita.paciente_id != self.paciente_id:
                raise ValidationError(
                    "El paciente de la consulta debe coincidir con el de la cita."
                )

    def __str__(self):
        return f"Consulta de {self.paciente} - {self.fecha:%Y-%m-%d}"


class Receta(TenantChildModel):
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.PROTECT,
        related_name="recetas",
    )
    fecha = models.DateTimeField(default=timezone.now)
    indicaciones = models.TextField(blank=True)

    tenant_lookup = "consulta__clinica"

    class Meta:
        verbose_name = "receta"
        verbose_name_plural = "recetas"
        ordering = ["-fecha"]
        indexes = [
            models.Index(
                fields=["consulta", "fecha"],
                name="receta_consulta_fecha_idx",
            ),
        ]

    def __str__(self):
        return f"Receta de {self.consulta} - {self.fecha:%Y-%m-%d}"


class MedicamentoRecetado(TenantChildModel):
    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name="medicamentos",
    )
    nombre_medicamento = models.CharField(max_length=150)
    dosis = models.CharField(max_length=50)
    frecuencia = models.CharField(max_length=50)
    duracion = models.CharField(max_length=50)

    tenant_lookup = "receta__consulta__clinica"

    class Meta:
        verbose_name = "medicamento recetado"
        verbose_name_plural = "medicamentos recetados"
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["receta"],
                name="medicamento_receta_idx",
            ),
        ]

    def __str__(self):
        return self.nombre_medicamento
