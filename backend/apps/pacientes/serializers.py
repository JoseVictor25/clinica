"""Serializadores de pacientes y sus antecedentes clínicos."""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.atencion.models import Cita, Consulta, EstudioMedico, Receta
from apps.atencion.serializers import MedicamentoRecetadoSerializer
from apps.seguridad.serializers import CuentaResumenSerializer

from .models import Alergia, Enfermedad, Paciente


class PacienteSerializer(serializers.ModelSerializer):
    """Expone los datos administrativos sin la cuenta vinculada."""

    tiene_usuario_vinculado = serializers.SerializerMethodField()
    cuenta = CuentaResumenSerializer(source="usuario", read_only=True)

    class Meta:
        model = Paciente
        fields = (
            "id",
            "clinica",
            "ci",
            "nombre",
            "apellido",
            "sexo",
            "fecha_nacimiento",
            "telefono",
            "email",
            "estado",
            "tiene_usuario_vinculado",
            "cuenta",
        )
        read_only_fields = ("id", "clinica")
        validators = []

    def get_tiene_usuario_vinculado(self, obj) -> bool:
        return obj.usuario_id is not None


class EnfermedadSerializer(serializers.ModelSerializer):
    """Contrato clínico; la historia se resuelve desde la URL."""

    class Meta:
        model = Enfermedad
        fields = ("id", "nombre", "tipo", "severidad", "fecha_deteccion")
        read_only_fields = ("id",)

    def validate_nombre(self, valor):
        nombre = valor.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return nombre


class AlergiaSerializer(serializers.ModelSerializer):
    """Contrato de alergias; paciente e historia provienen de la URL."""

    class Meta:
        model = Alergia
        fields = ("id", "nombre", "tipo", "severidad", "descripcion")
        read_only_fields = ("id",)

    def validate_nombre(self, valor):
        nombre = valor.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return nombre


class RechazaParametrosDesconocidosMixin:
    """Rechaza filtros no documentados en endpoints clínicos."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            desconocidos = sorted(set(data.keys()) - set(self.fields.keys()))
            if desconocidos:
                raise serializers.ValidationError(
                    {campo: ["Este parámetro no está permitido."] for campo in desconocidos}
                )
        return super().to_internal_value(data)


class HistorialConsultasParametrosSerializer(
    RechazaParametrosDesconocidosMixin,
    serializers.Serializer,
):
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
    medico_id = serializers.IntegerField(min_value=1, required=False)
    ordering = serializers.ChoiceField(
        choices=("fecha", "-fecha"), required=False, default="-fecha"
    )
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)

    def validate(self, attrs):
        if (
            attrs.get("fecha_desde")
            and attrs.get("fecha_hasta")
            and attrs["fecha_desde"] > attrs["fecha_hasta"]
        ):
            raise serializers.ValidationError(
                {"fecha_hasta": ["Debe ser igual o posterior a fecha_desde."]}
            )
        return attrs


class PacienteHistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ("id", "ci", "nombre", "apellido", "sexo", "fecha_nacimiento", "estado")
        read_only_fields = fields


class CitaHistorialSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = Cita
        fields = ("id", "fecha", "hora", "estado")
        read_only_fields = fields


class RecetaHistorialSerializer(serializers.ModelSerializer):
    medicamentos = MedicamentoRecetadoSerializer(many=True, read_only=True)
    puede_ver_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Receta
        fields = ("id", "fecha", "indicaciones", "puede_ver_detalle", "medicamentos")
        read_only_fields = fields

    def get_puede_ver_detalle(self, obj) -> bool:
        return obj.consulta.medico_id == self.context["medico_autenticado_id"]


class MedicoHistorialSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    especialidad = serializers.CharField()


class EstudioHistorialSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = EstudioMedico
        fields = (
            "id",
            "tipo_estudio",
            "tipo_estudio_display",
            "formato",
            "formato_display",
            "nombre_archivo",
            "estado",
            "estado_display",
            "observacion_lectura",
            "fecha_estudio",
        )
        read_only_fields = fields


class ConsultaHistorialSerializer(serializers.ModelSerializer):
    medico = serializers.SerializerMethodField()
    cita = CitaHistorialSerializer(read_only=True, allow_null=True)
    recetas = serializers.SerializerMethodField()
    estudios_medicos = EstudioHistorialSerializer(many=True, read_only=True)

    class Meta:
        model = Consulta
        fields = (
            "id", "fecha", "motivo", "observacion", "diagnostico",
            "medico", "cita", "recetas", "estudios_medicos",
        )
        read_only_fields = fields

    @extend_schema_field(MedicoHistorialSerializer)
    def get_medico(self, obj) -> dict:
        personal = obj.medico.personal
        return {
            "id": obj.medico_id,
            "nombre": f"{personal.nombre} {personal.apellido}",
            "especialidad": obj.medico.especialidad.nombre,
        }

    @extend_schema_field(RecetaHistorialSerializer(many=True))
    def get_recetas(self, obj) -> list[dict]:
        return RecetaHistorialSerializer(
            obj.recetas.all(), many=True, context=self.context
        ).data


class HistorialConsultasRespuestaSerializer(serializers.Serializer):
    paciente = PacienteHistorialSerializer()
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ConsultaHistorialSerializer(many=True)
