"""Contrato de la vinculación administrativa paciente-cuenta."""

from rest_framework import serializers


class VincularUsuarioPacienteSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            desconocidos = sorted(set(data.keys()) - {"usuario_id"})
            if desconocidos:
                raise serializers.ValidationError(
                    {campo: ["Este campo no está permitido."] for campo in desconocidos}
                )
        return super().to_internal_value(data)


class VincularUsuarioPacienteRespuestaSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    mensaje = serializers.CharField()
    paciente_id = serializers.IntegerField()
    usuario_id = serializers.IntegerField()
