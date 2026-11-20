"""Serializers para el Asistente Guía interactivo."""

from rest_framework import serializers


class AsistenteConsultaSerializer(serializers.Serializer):
    consulta = serializers.CharField(max_length=1000, trim_whitespace=True)
    ruta_actual = serializers.CharField(
        max_length=255,
        required=False,
        default="/",
        allow_blank=True,
    )

    def validate_consulta(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("La consulta no puede estar vacía.")
        return valor


class AsistenteRespuestaSerializer(serializers.Serializer):
    explicacion = serializers.CharField()
    pasos = serializers.ListField(child=serializers.CharField())
    id_accion = serializers.CharField(allow_null=True)
    id_menu = serializers.CharField(allow_null=True)
    ruta_objetivo = serializers.CharField(allow_null=True)
