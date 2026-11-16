"""Contratos HTTP de citas y disponibilidad."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta


class RechazaCamposDesconocidosMixin:
    """Evita que DRF ignore silenciosamente claves fuera del contrato."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            desconocidos = sorted(set(data.keys()) - set(self.fields.keys()))
            if desconocidos:
                raise serializers.ValidationError(
                    {
                        campo: ["Este campo no está permitido."]
                        for campo in desconocidos
                    }
                )
        return super().to_internal_value(data)


class CitaCrearSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    paciente_id = serializers.IntegerField(min_value=1)
    medico_id = serializers.IntegerField(min_value=1)
    fecha = serializers.DateField()
    hora = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    motivo = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate_motivo(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("El motivo es obligatorio.")
        return valor


class DisponibilidadParametrosSerializer(serializers.Serializer):
    paciente_id = serializers.IntegerField(min_value=1, required=True)
    medico_id = serializers.IntegerField(min_value=1, required=True)
    fecha = serializers.DateField(required=True)
    cita_id = serializers.IntegerField(min_value=1, required=False)


class AgendaMedicoParametrosSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    """Filtros permitidos para la agenda del médico autenticado."""

    fecha = serializers.DateField(required=False)
    estado = serializers.ChoiceField(
        choices=EstadoCita.choices,
        required=False,
    )
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
    )
    ordering = serializers.CharField(required=False)

    def validate_ordering(self, valor):
        campos = [campo.strip() for campo in valor.split(",")]
        permitidos = {"fecha", "hora", "id"}
        if not campos or any(
            not campo or campo.lstrip("-") not in permitidos
            for campo in campos
        ):
            raise serializers.ValidationError(
                "Use únicamente fecha, hora o id para ordenar."
            )
        return campos


class AccionCitaVaciaSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    """Contrato vacío para confirmar y cancelar."""


class CitaReprogramarSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    fecha = serializers.DateField(required=True)
    hora = serializers.TimeField(
        format="%H:%M",
        input_formats=["%H:%M"],
        required=True,
    )


class DisponibilidadSerializer(serializers.Serializer):
    paciente_id = serializers.IntegerField()
    medico_id = serializers.IntegerField()
    fecha = serializers.DateField()
    duracion_minutos = serializers.IntegerField()
    horarios = serializers.ListField(child=serializers.CharField())


class CitaSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField(read_only=True)
    paciente_nombre = serializers.SerializerMethodField()
    medico_id = serializers.IntegerField(read_only=True)
    medico_nombre = serializers.SerializerMethodField()
    especialidad_id = serializers.IntegerField(
        source="medico.especialidad_id",
        read_only=True,
    )
    especialidad_nombre = serializers.CharField(
        source="medico.especialidad.nombre",
        read_only=True,
    )
    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )
    consulta_id = serializers.SerializerMethodField()
    tiene_consulta = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = (
            "id",
            "paciente_id",
            "paciente_nombre",
            "medico_id",
            "medico_nombre",
            "especialidad_id",
            "especialidad_nombre",
            "fecha",
            "hora",
            "estado",
            "estado_display",
            "motivo",
            "consulta_id",
            "tiene_consulta",
        )
        read_only_fields = fields

    def get_paciente_nombre(self, obj) -> str:
        return f"{obj.paciente.apellido}, {obj.paciente.nombre}"

    def get_medico_nombre(self, obj) -> str:
        personal = obj.medico.personal
        return f"{personal.apellido}, {personal.nombre}"

    def get_consulta_id(self, obj) -> int | None:
        try:
            return obj.consulta.pk
        except Consulta.DoesNotExist:
            return None

    def get_tiene_consulta(self, obj) -> bool:
        return self.get_consulta_id(obj) is not None


class ConsultaCrearSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    cita_id = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(trim_whitespace=True)
    observacion = serializers.CharField(trim_whitespace=True)
    diagnostico = serializers.CharField(trim_whitespace=True)

    def _texto_obligatorio(self, valor, nombre):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError(f"{nombre} es obligatorio.")
        return valor

    def validate_motivo(self, valor):
        return self._texto_obligatorio(valor, "El motivo")

    def validate_observacion(self, valor):
        return self._texto_obligatorio(valor, "La observación")

    def validate_diagnostico(self, valor):
        return self._texto_obligatorio(valor, "El diagnóstico")


class MedicamentoRecetadoEntradaSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    nombre_medicamento = serializers.CharField(max_length=150, trim_whitespace=True)
    dosis = serializers.CharField(max_length=50, trim_whitespace=True)
    frecuencia = serializers.CharField(max_length=50, trim_whitespace=True)
    duracion = serializers.CharField(max_length=50, trim_whitespace=True)


class RecetaCrearSerializer(
    RechazaCamposDesconocidosMixin,
    serializers.Serializer,
):
    indicaciones = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=True
    )
    medicamentos = MedicamentoRecetadoEntradaSerializer(many=True, allow_empty=False)


class MedicamentoRecetadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentoRecetado
        fields = ("id", "nombre_medicamento", "dosis", "frecuencia", "duracion")
        read_only_fields = fields


class AdvertenciaAlergiaSerializer(serializers.Serializer):
    alergia_id = serializers.IntegerField()
    nombre_alergia = serializers.CharField()
    severidad = serializers.CharField()
    medicamento = serializers.CharField()
    mensaje = serializers.CharField()


class RecetaSerializer(serializers.ModelSerializer):
    consulta_id = serializers.IntegerField(read_only=True)
    paciente_id = serializers.IntegerField(source="consulta.paciente_id", read_only=True)
    paciente_nombre = serializers.SerializerMethodField()
    medico_id = serializers.IntegerField(source="consulta.medico_id", read_only=True)
    medico_nombre = serializers.SerializerMethodField()
    medicamentos = MedicamentoRecetadoSerializer(many=True, read_only=True)
    advertencias_alergia = serializers.SerializerMethodField()

    class Meta:
        model = Receta
        fields = (
            "id", "consulta_id", "fecha", "paciente_id", "paciente_nombre",
            "medico_id", "medico_nombre", "indicaciones", "medicamentos",
            "advertencias_alergia",
        )
        read_only_fields = fields

    def get_paciente_nombre(self, obj) -> str:
        return f"{obj.consulta.paciente.apellido}, {obj.consulta.paciente.nombre}"

    def get_medico_nombre(self, obj) -> str:
        personal = obj.consulta.medico.personal
        return f"{personal.apellido}, {personal.nombre}"

    @extend_schema_field(AdvertenciaAlergiaSerializer(many=True))
    def get_advertencias_alergia(self, obj) -> list[dict]:
        from .services import calcular_advertencias_alergia
        return calcular_advertencias_alergia(obj)


class RecetaResumenSerializer(serializers.ModelSerializer):
    cantidad_medicamentos = serializers.SerializerMethodField()

    class Meta:
        model = Receta
        fields = ("id", "fecha", "indicaciones", "cantidad_medicamentos")
        read_only_fields = fields

    def get_cantidad_medicamentos(self, obj) -> int:
        return len(obj.medicamentos.all())


class ConsultaSerializer(serializers.ModelSerializer):
    cita_id = serializers.IntegerField(read_only=True)
    paciente_id = serializers.IntegerField(read_only=True)
    paciente_nombre = serializers.SerializerMethodField()
    medico_id = serializers.IntegerField(read_only=True)
    medico_nombre = serializers.SerializerMethodField()
    estado_cita = serializers.CharField(source="cita.estado", read_only=True)
    recetas = RecetaResumenSerializer(many=True, read_only=True)

    class Meta:
        model = Consulta
        fields = (
            "id",
            "cita_id",
            "fecha",
            "paciente_id",
            "paciente_nombre",
            "medico_id",
            "medico_nombre",
            "motivo",
            "observacion",
            "diagnostico",
            "estado_cita",
            "recetas",
        )
        read_only_fields = fields

    def get_paciente_nombre(self, obj) -> str:
        return f"{obj.paciente.apellido}, {obj.paciente.nombre}"

    def get_medico_nombre(self, obj) -> str:
        personal = obj.medico.personal
        return f"{personal.apellido}, {personal.nombre}"


class AgendaMedicoRespuestaSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CitaSerializer(many=True)


class EstadoCitaSerializer(serializers.Serializer):
    valor = serializers.ChoiceField(choices=EstadoCita.choices)

