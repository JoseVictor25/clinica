"""Contratos de lectura exclusivos del portal del paciente."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.pacientes.models import Alergia, Enfermedad, HistoriaClinica, Paciente

from .models import Cita, Consulta, MedicamentoRecetado, Receta


class RechazaParametrosPortalMixin:
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            desconocidos = sorted(set(data.keys()) - set(self.fields.keys()))
            if desconocidos:
                raise serializers.ValidationError(
                    {campo: ["Este parámetro no está permitido."] for campo in desconocidos}
                )
        return super().to_internal_value(data)


class FiltrosFechasPortalSerializer(RechazaParametrosPortalMixin, serializers.Serializer):
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
    ordering = serializers.ChoiceField(choices=("fecha", "-fecha"), default="-fecha", required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)

    def validate(self, attrs):
        if attrs.get("fecha_desde") and attrs.get("fecha_hasta") and attrs["fecha_desde"] > attrs["fecha_hasta"]:
            raise serializers.ValidationError({"fecha_hasta": ["Debe ser igual o posterior a fecha_desde."]})
        return attrs


class FiltrosCitasPortalSerializer(FiltrosFechasPortalSerializer):
    estado = serializers.ChoiceField(choices=Cita._meta.get_field("estado").choices, required=False)


class PacientePortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ("id", "ci", "nombre", "apellido", "sexo", "fecha_nacimiento", "telefono", "email", "estado")
        read_only_fields = fields


class EnfermedadPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enfermedad
        fields = ("id", "nombre", "tipo", "severidad", "fecha_deteccion")
        read_only_fields = fields


class AlergiaPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alergia
        fields = ("id", "nombre", "tipo", "severidad", "descripcion")
        read_only_fields = fields


class HistoriaPortalSerializer(serializers.ModelSerializer):
    enfermedades = EnfermedadPortalSerializer(many=True, read_only=True)
    alergias = AlergiaPortalSerializer(many=True, read_only=True)

    class Meta:
        model = HistoriaClinica
        fields = ("id", "fecha_apertura", "grupo_sanguineo", "observaciones_generales", "estado", "enfermedades", "alergias")
        read_only_fields = fields


def _medico(obj):
    personal = obj.medico.personal
    return {
        "id": obj.medico_id,
        "nombre": f"{personal.nombre} {personal.apellido}",
        "especialidad": obj.medico.especialidad.nombre,
    }


class MedicoPortalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    especialidad = serializers.CharField()


class CitaPortalSerializer(serializers.ModelSerializer):
    medico = serializers.SerializerMethodField()
    modalidad_display = serializers.CharField(source="get_modalidad_display", read_only=True)

    class Meta:
        model = Cita
        fields = ("id", "fecha", "hora", "estado", "modalidad", "modalidad_display", "link_videollamada", "motivo", "medico")
        read_only_fields = fields

    @extend_schema_field(MedicoPortalSerializer)
    def get_medico(self, obj) -> dict:
        return _medico(obj)


class CitaConsultaPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = ("id", "fecha", "hora", "estado")
        read_only_fields = fields


class RecetaResumenPortalSerializer(serializers.ModelSerializer):
    cantidad_medicamentos = serializers.SerializerMethodField()

    class Meta:
        model = Receta
        fields = ("id", "fecha", "indicaciones", "cantidad_medicamentos")
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField)
    def get_cantidad_medicamentos(self, obj) -> int:
        return len(obj.medicamentos.all())


class ConsultaPortalSerializer(serializers.ModelSerializer):
    medico = serializers.SerializerMethodField()
    cita = CitaConsultaPortalSerializer(read_only=True, allow_null=True)
    recetas = RecetaResumenPortalSerializer(many=True, read_only=True)

    class Meta:
        model = Consulta
        fields = ("id", "fecha", "motivo", "observacion", "diagnostico", "medico", "cita", "recetas")
        read_only_fields = fields

    @extend_schema_field(MedicoPortalSerializer)
    def get_medico(self, obj) -> dict:
        return _medico(obj)


class MedicamentoPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentoRecetado
        fields = ("id", "nombre_medicamento", "dosis", "frecuencia", "duracion")
        read_only_fields = fields


class ConsultaRecetaPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consulta
        fields = ("id", "fecha", "motivo", "diagnostico")
        read_only_fields = fields


class RecetaDetallePortalSerializer(serializers.ModelSerializer):
    consulta = ConsultaRecetaPortalSerializer(read_only=True)
    medico = serializers.SerializerMethodField()
    medicamentos = MedicamentoPortalSerializer(many=True, read_only=True)

    class Meta:
        model = Receta
        fields = ("id", "fecha", "indicaciones", "consulta", "medico", "medicamentos")
        read_only_fields = fields

    @extend_schema_field(MedicoPortalSerializer)
    def get_medico(self, obj) -> dict:
        return _medico(obj.consulta)


class RespuestaCitasPortalSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CitaPortalSerializer(many=True)


class RespuestaConsultasPortalSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ConsultaPortalSerializer(many=True)
