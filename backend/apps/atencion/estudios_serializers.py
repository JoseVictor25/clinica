"""Serializers para estudios médicos."""

from rest_framework import serializers

from .estudios_services import cita_cerrada_para_estudios
from .models import EstudioMedico, TipoEstudio


class EstudioMedicoCrearSerializer(serializers.Serializer):
    tipo_estudio = serializers.ChoiceField(choices=TipoEstudio.choices)
    cita_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    paciente_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    archivo = serializers.FileField()


class EstudioMedicoActualizarSerializer(serializers.Serializer):
    tipo_estudio = serializers.ChoiceField(choices=TipoEstudio.choices, required=False)
    archivo = serializers.FileField(required=False)


class EstudioMedicoRevisarSerializer(serializers.Serializer):
    observacion_lectura = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    consulta_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class EstudioMedicoSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField(read_only=True)
    paciente_nombre = serializers.SerializerMethodField()
    historia_clinica_id = serializers.IntegerField(read_only=True)
    cita_id = serializers.IntegerField(read_only=True)
    consulta_id = serializers.IntegerField(read_only=True)
    medico_id = serializers.IntegerField(read_only=True)
    medico_nombre = serializers.SerializerMethodField()
    tipo_estudio_display = serializers.CharField(
        source="get_tipo_estudio_display",
        read_only=True,
    )
    formato_display = serializers.CharField(
        source="get_formato_display",
        read_only=True,
    )
    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )
    puede_modificar = serializers.SerializerMethodField()

    class Meta:
        model = EstudioMedico
        fields = (
            "id",
            "paciente_id",
            "paciente_nombre",
            "historia_clinica_id",
            "cita_id",
            "consulta_id",
            "medico_id",
            "medico_nombre",
            "tipo_estudio",
            "tipo_estudio_display",
            "formato",
            "formato_display",
            "nombre_archivo",
            "url_archivo",
            "ruta_storage",
            "estado",
            "estado_display",
            "observacion_lectura",
            "fecha_estudio",
            "puede_modificar",
        )
        read_only_fields = fields

    def get_paciente_nombre(self, obj) -> str:
        return f"{obj.paciente.apellido}, {obj.paciente.nombre}"

    def get_medico_nombre(self, obj) -> str | None:
        if not obj.medico_id:
            return None
        personal = obj.medico.personal
        return f"{personal.apellido}, {personal.nombre}"

    def get_puede_modificar(self, obj) -> bool:
        if obj.consulta_id is not None:
            return False
        return not cita_cerrada_para_estudios(obj.cita)
