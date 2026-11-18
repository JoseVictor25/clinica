"""Contratos compartidos para crear cuentas vinculadas."""

from rest_framework import serializers

from apps.core.fields import TenantRelatedField

from .models import Rol


class RechazaCamposDesconocidosMixin:
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            desconocidos = sorted(set(data.keys()) - set(self.fields.keys()))
            if desconocidos:
                raise serializers.ValidationError(
                    {campo: ["Este campo no está permitido."] for campo in desconocidos}
                )
        return super().to_internal_value(data)


class CrearCuentaPersonalSerializer(
    RechazaCamposDesconocidosMixin, serializers.Serializer
):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    roles = TenantRelatedField(Rol, many=True, required=False)


class CrearCuentaPacienteSerializer(
    RechazaCamposDesconocidosMixin, serializers.Serializer
):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class BuscarCuentasElegiblesSerializer(
    RechazaCamposDesconocidosMixin, serializers.Serializer
):
    search = serializers.CharField(required=False, allow_blank=True, max_length=254)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)
