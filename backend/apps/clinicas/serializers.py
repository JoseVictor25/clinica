"""Serializers de clínicas, planes y suscripciones."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.core.api_exceptions import DatosInvalidos

from .models import Clinica, PlanSuscripcion, Suscripcion


class ClinicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = (
            "id",
            "nombre",
            "direccion",
            "telefono",
            "email",
            "nit",
            "estado",
        )
        read_only_fields = ("id",)


class AdminInicialSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value):
        try:
            validate_password(value)
        except Exception as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class ClinicaCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    direccion = serializers.CharField(max_length=255)
    telefono = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    nit = serializers.CharField(max_length=20)
    admin = AdminInicialSerializer()


class PlanSuscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanSuscripcion
        fields = (
            "id",
            "nombre",
            "precio",
            "max_usuarios",
            "descripcion",
            "activo",
        )
        read_only_fields = ("id",)


class SuscripcionSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )
    vigente = serializers.SerializerMethodField()

    class Meta:
        model = Suscripcion
        fields = (
            "id",
            "clinica",
            "clinica_nombre",
            "plan",
            "plan_nombre",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "vigente",
        )
        read_only_fields = fields

    def get_vigente(self, obj) -> bool:
        from .services import suscripcion_vigente

        return suscripcion_vigente(obj.clinica) is not None


class SuscripcionCreateSerializer(serializers.Serializer):
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=PlanSuscripcion.objects.all(), source="plan"
    )
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField()

    def validate(self, attrs):
        from django.utils import timezone

        inicio = attrs.get("fecha_inicio") or timezone.localdate()
        if attrs["fecha_fin"] < inicio:
            raise DatosInvalidos(
                "La fecha de fin no puede ser anterior a la fecha de inicio.",
                codigo="fechas_invalidas",
            )
        attrs["fecha_inicio"] = inicio
        return attrs


class RenovarSuscripcionSerializer(serializers.Serializer):
    nueva_fecha_fin = serializers.DateField()


class CambiarPlanSerializer(serializers.Serializer):
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=PlanSuscripcion.objects.all(), source="plan"
    )
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField()

    def validate(self, attrs):
        from django.utils import timezone

        inicio = attrs.get("fecha_inicio") or timezone.localdate()
        if attrs["fecha_fin"] < inicio:
            raise DatosInvalidos(
                "La fecha de fin no puede ser anterior a la fecha de inicio.",
                codigo="fechas_invalidas",
            )
        attrs["fecha_inicio"] = inicio
        return attrs
