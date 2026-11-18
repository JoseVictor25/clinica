"""Serializers de personal, especialidades, médicos y horarios."""

from rest_framework import serializers

from apps.core.fields import TenantRelatedField
from apps.seguridad.serializers import CuentaResumenSerializer

from .models import Especialidad, HorarioAtencion, Medico, Personal


class PersonalSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )
    cuenta = CuentaResumenSerializer(source="usuario", read_only=True)

    class Meta:
        model = Personal
        fields = (
            "id",
            "clinica",
            "clinica_nombre",
            "usuario",
            "cuenta",
            "ci",
            "nombre",
            "apellido",
            "telefono",
            "cargo",
            "fecha_ingreso",
            "estado",
        )
        read_only_fields = ("id", "clinica", "clinica_nombre")


class EspecialidadSerializer(serializers.ModelSerializer):
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )

    class Meta:
        model = Especialidad
        fields = (
            "id",
            "clinica",
            "clinica_nombre",
            "nombre",
            "descripcion",
            "estado",
        )
        read_only_fields = ("id", "clinica", "clinica_nombre")


class MedicoSerializer(serializers.ModelSerializer):
    personal = TenantRelatedField(Personal)
    especialidad = TenantRelatedField(Especialidad)
    especialidades = TenantRelatedField(
        Especialidad, many=True, required=False
    )
    # Se declara sin UniqueValidator para que el servicio devuelva 409
    # (colegiatura_duplicada) en lugar de un 400 genérico.
    numero_colegiatura = serializers.CharField(max_length=30)
    personal_nombre = serializers.SerializerMethodField()
    especialidad_nombre = serializers.CharField(
        source="especialidad.nombre", read_only=True
    )
    especialidades_nombres = serializers.SerializerMethodField()
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )

    class Meta:
        model = Medico
        fields = (
            "id",
            "clinica",
            "clinica_nombre",
            "personal",
            "personal_nombre",
            "especialidad",
            "especialidad_nombre",
            "especialidades",
            "especialidades_nombres",
            "numero_colegiatura",
            "estado",
        )
        read_only_fields = ("id", "clinica", "clinica_nombre")

    def get_personal_nombre(self, obj) -> str:
        return str(obj.personal)

    def get_especialidades_nombres(self, obj) -> list[str]:
        return [especialidad.nombre for especialidad in obj.especialidades.all()]


class HorarioAtencionSerializer(serializers.ModelSerializer):
    # Un médico crea sus horarios sin enviar `medico`: el servidor lo resuelve
    # a partir de su registro de Personal/Médico vinculado.
    medico = TenantRelatedField(Medico, required=False)
    medico_nombre = serializers.SerializerMethodField()

    class Meta:
        model = HorarioAtencion
        fields = (
            "id",
            "medico",
            "medico_nombre",
            "dia_semana",
            "hora_inicio",
            "hora_fin",
        )
        read_only_fields = ("id", "medico_nombre")
        # El solapamiento y la unicidad se validan en el servicio para devolver
        # un código de negocio (horario_solapado) en lugar de un 400 genérico.
        validators = []

    def get_medico_nombre(self, obj) -> str:
        return str(obj.medico)

    def validate(self, attrs):
        inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if inicio and fin and inicio >= fin:
            raise serializers.ValidationError(
                {"hora_fin": ["La hora de fin debe ser posterior al inicio."]}
            )
        return attrs
