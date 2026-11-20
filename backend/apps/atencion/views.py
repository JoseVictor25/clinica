"""API REST de citas y disponibilidad."""
from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import (
    EsAdminClinicaORecepcionista,
    EsMedico,
    EsMedicoOPaciente,
    TieneClinica,
    TieneSuscripcionVigente,
)
from apps.core.api_exceptions import DatosInvalidos
from apps.core.querysets import queryset_tenant
from apps.notificaciones.services import programar_notificacion_cita

from .models import Cita, Consulta, EstadoCita
from .serializers import (
    AccionCitaVaciaSerializer,
    AgendaMedicoParametrosSerializer,
    AgendaMedicoRespuestaSerializer,
    CitaCrearSerializer,
    CitaReprogramarSerializer,
    CitaSerializer,
    ConsultaCrearSerializer,
    ConsultaSerializer,
    DisponibilidadParametrosSerializer,
    DisponibilidadSerializer,
    RecetaCrearSerializer,
    RecetaSerializer,
)
from .services import (
    cancelar_cita,
    confirmar_cita,
    crear_consulta,
    crear_cita,
    obtener_agenda_medico,
    obtener_cita_sala_virtual,
    obtener_consulta_medico,
    obtener_disponibilidad,
    crear_receta,
    obtener_receta_medico,
    reprogramar_cita,
)

ERRORES_RECETA = {
    400: OpenApiResponse(
        description="Datos inválidos o medicamentos ausentes (datos_invalidos, medicamentos_requeridos)."
    ),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description="Rol no permitido, clínica inactiva o suscripción vencida."
    ),
    404: OpenApiResponse(
        description="Consulta o receta ajena, inexistente o de otro médico (no_encontrado)."
    ),
    409: OpenApiResponse(
        description=(
            "medico_no_vinculado, medico_inactivo, paciente_inactivo, "
            "historia_no_disponible o consulta_no_atendida."
        )
    ),
}

ERRORES_CITA = {
    400: OpenApiResponse(
        description="Datos inválidos: fecha_cita_pasada, hora_cita_pasada o fuera_horario."
    ),
    401: OpenApiResponse(description="No autenticado."),
    403: OpenApiResponse(
        description="Rol no permitido, clínica inactiva o suscripción vencida."
    ),
    404: OpenApiResponse(
        description="Recurso inexistente o perteneciente a otra clínica."
    ),
    409: OpenApiResponse(
        description=(
            "horario_no_disponible, paciente_no_disponible, "
            "paciente_inactivo, medico_inactivo, transicion_cita_invalida "
            "o cita_no_reprogramable."
        )
    ),
}

ERRORES_CONSULTA = {
    400: OpenApiResponse(description="Datos de entrada inválidos (datos_invalidos)."),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description=(
            "Rol no permitido, clínica inactiva o suscripción vencida "
            "(permiso_denegado, clinica_inactiva, suscripcion_vencida)."
        )
    ),
    404: OpenApiResponse(
        description="Cita o consulta inexistente, ajena o de otro médico (no_encontrado)."
    ),
    409: OpenApiResponse(
        description=(
            "Conflictos: medico_no_vinculado, medico_inactivo, paciente_inactivo, "
            "historia_no_disponible, cita_no_confirmada o consulta_ya_registrada."
        )
    ),
}


class MiAgendaMedicoView(generics.GenericAPIView):
    """Agenda estática de solo lectura; evita colisionar con /citas/{id}/."""

    serializer_class = CitaSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedico)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Devuelve la agenda personal, paginada y de solo lectura del médico "
            "autenticado. El médico se resuelve desde Usuario → Personal → "
            "Medico dentro de la clínica activa; no se acepta medico_id. Sin "
            "fecha utiliza la fecha local configurada en Django. Incluye todos "
            "los estados salvo que se indique estado y ordena de forma estable "
            "por fecha, hora e id. Requiere rol Médico activo, clínica activa y "
            "suscripción vigente."
        ),
        parameters=[
            OpenApiParameter(
                "fecha",
                OpenApiTypes.DATE,
                required=False,
                description="Fecha exacta; por defecto timezone.localdate().",
            ),
            OpenApiParameter(
                "estado", str, required=False, enum=EstadoCita.values
            ),
            OpenApiParameter(
                "ordering",
                str,
                required=False,
                description=(
                    "fecha, hora o id; admite prefijo - y listas separadas por coma."
                ),
            ),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={
            200: AgendaMedicoRespuestaSerializer,
            400: OpenApiResponse(
                description=(
                    "Filtros inválidos o medico_id no permitido (datos_invalidos)."
                )
            ),
            401: OpenApiResponse(description="No autenticado (no_autenticado)."),
            403: OpenApiResponse(
                description=(
                    "Rol no permitido, clínica inactiva o suscripción vencida "
                    "(permiso_denegado, clinica_inactiva, suscripcion_vencida)."
                )
            ),
            409: OpenApiResponse(
                description=(
                    "Médico no vinculado o inactivo "
                    "(medico_no_vinculado, medico_inactivo)."
                )
            ),
        },
    )
    def get(self, request):
        parametros = AgendaMedicoParametrosSerializer(
            data=request.query_params
        )
        parametros.is_valid(raise_exception=True)
        datos = parametros.validated_data
        queryset = obtener_agenda_medico(
            usuario=request.user,
            clinica=request.user.clinica,
            fecha=datos.get("fecha", timezone.localdate()),
            estado=datos.get("estado"),
            ordering=datos.get("ordering"),
        )
        pagina = self.paginate_queryset(queryset)
        if pagina is not None:
            serializado = CitaSerializer(pagina, many=True).data
            return self.get_paginated_response(serializado)
        return Response(CitaSerializer(queryset, many=True).data)


@extend_schema_view(
    create=extend_schema(
        tags=["Consultas"],
        description=(
            "Registra una consulta para una cita CONFIRMADA del médico autenticado. "
            "Solo acepta cita_id, motivo, observacion y diagnostico. La clínica, "
            "el médico, el paciente, la fecha y la historia se resuelven en el "
            "servidor. La consulta, la actualización de la historia y el cambio de "
            "la cita a ATENDIDA se realizan en una sola transacción."
        ),
        request=ConsultaCrearSerializer,
        responses={201: ConsultaSerializer, **ERRORES_CONSULTA},
    ),
    retrieve=extend_schema(
        tags=["Consultas"],
        description=(
            "Devuelve una consulta propia del médico autenticado. No revela "
            "consultas de otros médicos ni de otras clínicas."
        ),
        responses={200: ConsultaSerializer, **ERRORES_CONSULTA},
    ),
)
class ConsultaViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Consulta.all_objects.none()
    serializer_class = ConsultaSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedico)
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        entrada = ConsultaCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        consulta = crear_consulta(
            usuario=request.user,
            clinica=request.user.clinica,
            datos=entrada.validated_data,
        )
        return Response(
            ConsultaSerializer(consulta).data,
            status=status.HTTP_201_CREATED,
        )

    def get_object(self):
        return obtener_consulta_medico(
            usuario=self.request.user,
            clinica=self.request.user.clinica,
            consulta_id=self.kwargs["pk"],
        )


class RecetaCrearView(generics.GenericAPIView):
    serializer_class = RecetaCrearSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedico)

    @extend_schema(
        tags=["Recetas"],
        description=(
            "Emite una receta para una consulta propia asociada a una cita ATENDIDA. "
            "Exige al menos un medicamento, rechaza campos desconocidos y crea receta "
            "y medicamentos en una sola transacción. Se permiten varias recetas por "
            "consulta. Las advertencias comparan exactamente nombres normalizados con "
            "NFKC, espacios colapsados y casefold contra alergias MEDICAMENTO actuales; "
            "son informativas, no bloqueantes y no se persisten."
        ),
        request=RecetaCrearSerializer,
        responses={201: RecetaSerializer, **ERRORES_RECETA},
    )
    def post(self, request, consulta_id):
        if not hasattr(request.data, "get") or request.data.get("medicamentos") in (None, []):
            raise DatosInvalidos(
                "Debe incluir al menos un medicamento.",
                codigo="medicamentos_requeridos",
                detalles={"medicamentos": ["Incluya al menos un medicamento."]},
            )
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        receta = crear_receta(
            usuario=request.user,
            clinica=request.user.clinica,
            consulta_id=consulta_id,
            datos=entrada.validated_data,
        )
        return Response(RecetaSerializer(receta).data, status=status.HTTP_201_CREATED)


class RecetaDetalleView(generics.GenericAPIView):
    serializer_class = RecetaSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedico)

    @extend_schema(
        tags=["Recetas"],
        description=(
            "Devuelve una receta propia con sus medicamentos. Las advertencias se "
            "recalculan con las alergias actuales y pueden variar sin modificar la receta."
        ),
        responses={200: RecetaSerializer, **ERRORES_RECETA},
    )
    def get(self, request, pk):
        receta = obtener_receta_medico(
            usuario=request.user,
            clinica=request.user.clinica,
            receta_id=pk,
        )
        return Response(self.get_serializer(receta).data)


@extend_schema_view(
    list=extend_schema(
        tags=["Citas"],
        description=(
            "Lista citas de la clínica autenticada con aislamiento multitenant."
        ),
        parameters=[
            OpenApiParameter("fecha", OpenApiTypes.DATE),
            OpenApiParameter("paciente_id", OpenApiTypes.INT),
            OpenApiParameter("medico_id", OpenApiTypes.INT),
            OpenApiParameter("estado", str, enum=EstadoCita.values),
            OpenApiParameter("ordering", str, description="fecha, hora"),
        ],
        responses={200: CitaSerializer(many=True), **ERRORES_CITA},
    ),
    create=extend_schema(
        tags=["Citas"],
        description=(
            "Crea una cita PROGRAMADA. Solo acepta paciente_id, medico_id, "
            "fecha, hora y motivo. La clínica se obtiene del usuario; la "
            "especialidad no se guarda y la duración técnica de 30 minutos "
            "no se persiste. Valida fechas y horas pasadas, recursos activos, "
            "bloques del horario y solapamientos del médico y del paciente. "
            "Cada cita ocupa el intervalo semiabierto [inicio, inicio + 30 minutos) "
            "en la zona horaria de Django. El servicio vuelve a validar estas "
            "reglas dentro de una transacción con bloqueos de paciente, médico "
            "y personal. Los errores de fecha u hora se incluyen en detalles."
        ),
        request=CitaCrearSerializer,
        responses={201: CitaSerializer, **ERRORES_CITA},
    ),
    retrieve=extend_schema(
        tags=["Citas"],
        responses={200: CitaSerializer, **ERRORES_CITA},
    ),
)
class CitaViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CitaSerializer
    permission_classes = (
        TieneClinica,
        TieneSuscripcionVigente,
        EsAdminClinicaORecepcionista,
    )
    http_method_names = ["get", "post", "head", "options"]
    ordering_fields = ("fecha", "hora")
    ordering = ("fecha", "hora")

    def get_queryset(self):
        queryset = queryset_tenant(Cita, self.request).select_related(
            "paciente",
            "medico__personal",
            "medico__especialidad",
        )
        parametros = self.request.query_params

        fecha = parametros.get("fecha")
        if fecha:
            try:
                fecha = date.fromisoformat(fecha)
            except ValueError as exc:
                raise ValidationError(
                    {"fecha": ["Use el formato YYYY-MM-DD."]}
                ) from exc
            queryset = queryset.filter(fecha=fecha)

        for campo in ("paciente_id", "medico_id"):
            valor = parametros.get(campo)
            if valor not in (None, ""):
                try:
                    valor = int(valor)
                    if valor <= 0:
                        raise ValueError
                except (TypeError, ValueError) as exc:
                    raise ValidationError(
                        {campo: ["Debe ser un entero válido."]}
                    ) from exc
                queryset = queryset.filter(**{campo: valor})

        estado = parametros.get("estado")
        if estado:
            if estado not in EstadoCita.values:
                raise ValidationError({"estado": ["Estado de cita inválido."]})
            queryset = queryset.filter(estado=estado)
        return queryset

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def create(self, request, *args, **kwargs):
        entrada = CitaCrearSerializer(
            data=request.data,
            context={"request": request},
        )
        entrada.is_valid(raise_exception=True)
        cita = crear_cita(request.user.clinica, entrada.validated_data)
        programar_notificacion_cita(cita_id=cita.pk, evento="programada")
        return Response(
            CitaSerializer(cita).data,
            status=status.HTTP_201_CREATED,
        )

    def _validar_cuerpo_vacio(self, request):
        entrada = AccionCitaVaciaSerializer(data=request.data or {})
        entrada.is_valid(raise_exception=True)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Confirma una cita PROGRAMADA dentro de la clínica autenticada. "
            "No acepta campos y aplica PROGRAMADA → CONFIRMADA dentro de una "
            "transacción con bloqueo de la cita."
        ),
        request=AccionCitaVaciaSerializer,
        responses={200: CitaSerializer, **ERRORES_CITA},
    )
    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        self._validar_cuerpo_vacio(request)
        cita = confirmar_cita(
            clinica=request.user.clinica,
            cita_id=pk,
        )
        programar_notificacion_cita(cita_id=cita.pk, evento="confirmada")
        return Response(CitaSerializer(cita).data)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Cancela una cita PROGRAMADA o CONFIRMADA y libera su intervalo. "
            "No acepta campos y puede ejecutarse aunque la fecha haya pasado "
            "o sus participantes estén inactivos."
        ),
        request=AccionCitaVaciaSerializer,
        responses={200: CitaSerializer, **ERRORES_CITA},
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        self._validar_cuerpo_vacio(request)
        cita = cancelar_cita(
            clinica=request.user.clinica,
            cita_id=pk,
        )
        programar_notificacion_cita(cita_id=cita.pk, evento="cancelada")
        return Response(CitaSerializer(cita).data)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Reprograma una cita PROGRAMADA o CONFIRMADA, conservando paciente, "
            "médico, motivo y clínica. Solo acepta fecha y hora; reutiliza las "
            "reglas temporales, horarios y solapamientos de S2-06, excluye "
            "únicamente la propia cita y deja el estado en PROGRAMADA. La "
            "operación bloquea paciente, médico, personal y cita en ese orden."
        ),
        request=CitaReprogramarSerializer,
        responses={200: CitaSerializer, **ERRORES_CITA},
    )
    @action(detail=True, methods=["post"], url_path="reprogramar")
    def reprogramar(self, request, pk=None):
        entrada = CitaReprogramarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cita = reprogramar_cita(
            clinica=request.user.clinica,
            cita_id=pk,
            **entrada.validated_data,
        )
        programar_notificacion_cita(cita_id=cita.pk, evento="reprogramada")
        return Response(CitaSerializer(cita).data)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Calcula bloques disponibles de 30 minutos desde los horarios "
            "del médico. Excluye bloques pasados y los solapados con citas "
            "activas del médico o del paciente mediante intervalos semiabiertos. "
            "Usa la zona horaria configurada, exige participantes activos y "
            "mantiene el aislamiento por clínica. Los errores de fecha se "
            "incluyen en detalles."
        ),
        parameters=[
            OpenApiParameter("paciente_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("medico_id", OpenApiTypes.INT, required=True),
            OpenApiParameter("fecha", OpenApiTypes.DATE, required=True),
            OpenApiParameter(
                "cita_id",
                OpenApiTypes.INT,
                required=False,
                description=(
                    "Cita PROGRAMADA o CONFIRMADA del mismo paciente y médico "
                    "que se excluye de forma segura al calcular una reprogramación."
                ),
            ),
        ],
        responses={200: DisponibilidadSerializer, **ERRORES_CITA},
    )
    @action(detail=False, methods=["get"], url_path="disponibilidad")
    def disponibilidad(self, request):
        parametros = DisponibilidadParametrosSerializer(
            data=request.query_params
        )
        parametros.is_valid(raise_exception=True)
        resultado = obtener_disponibilidad(
            request.user.clinica,
            **parametros.validated_data,
        )
        return Response(DisponibilidadSerializer(resultado).data)


class SalaVirtualCitaView(generics.GenericAPIView):
    """Devuelve los datos de una cita virtual para el médico o paciente asignado."""

    serializer_class = CitaSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedicoOPaciente)

    @extend_schema(
        tags=["Citas"],
        description=(
            "Devuelve los datos de la cita virtual (incluido link_videollamada) "
            "únicamente al médico o al paciente asignado a esa cita."
        ),
        responses={200: CitaSerializer, **ERRORES_CITA},
    )
    def get(self, request, pk):
        cita = obtener_cita_sala_virtual(
            usuario=request.user,
            clinica=request.user.clinica,
            cita_id=pk,
        )
        return Response(self.get_serializer(cita).data)

