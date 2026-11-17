"""Endpoints GET del portal del paciente."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.response import Response

from apps.core.permissions import EsPaciente, TieneClinica, TieneSuscripcionVigente

from .portal_paciente_serializers import (
    ConsultaPortalSerializer,
    FiltrosCitasPortalSerializer,
    FiltrosFechasPortalSerializer,
    HistoriaPortalSerializer,
    PacientePortalSerializer,
    RecetaDetallePortalSerializer,
    RespuestaCitasPortalSerializer,
    RespuestaConsultasPortalSerializer,
    CitaPortalSerializer,
)
from .portal_paciente_services import (
    obtener_citas_portal,
    obtener_consultas_portal,
    obtener_historia_portal,
    obtener_paciente_autenticado,
    obtener_receta_portal,
)


PERMISOS = (TieneClinica, TieneSuscripcionVigente, EsPaciente)
ERRORES = {
    400: OpenApiResponse(description="Parámetros inválidos (datos_invalidos)."),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(description="Rol, clínica o suscripción no permitidos."),
    404: OpenApiResponse(description="Recurso inexistente o ajeno (no_encontrado)."),
    409: OpenApiResponse(description="Paciente no vinculado/inactivo o historia no disponible."),
}


class BasePortalPacienteView(generics.GenericAPIView):
    permission_classes = PERMISOS
    http_method_names = ["get", "head", "options"]

    def paciente(self):
        if not hasattr(self, "_paciente_portal"):
            self._paciente_portal = obtener_paciente_autenticado(usuario=self.request.user, clinica=self.request.user.clinica)
        return self._paciente_portal


class MiInformacionView(BasePortalPacienteView):
    serializer_class = PacientePortalSerializer

    @extend_schema(tags=["Portal del paciente"], responses={200: PacientePortalSerializer, **ERRORES}, description="Devuelve únicamente los datos generales del paciente vinculado al usuario autenticado.")
    def get(self, request):
        return Response(self.get_serializer(self.paciente()).data)


class MiHistoriaView(BasePortalPacienteView):
    serializer_class = HistoriaPortalSerializer

    @extend_schema(tags=["Portal del paciente"], responses={200: HistoriaPortalSerializer, **ERRORES}, description="Devuelve la historia, enfermedades y alergias propias. Solo este endpoint exige historia clínica.")
    def get(self, request):
        historia = obtener_historia_portal(paciente=self.paciente(), clinica=request.user.clinica)
        return Response(self.get_serializer(historia).data)


PARAMETROS_COMUNES = [
    OpenApiParameter("fecha_desde", OpenApiTypes.DATE), OpenApiParameter("fecha_hasta", OpenApiTypes.DATE),
    OpenApiParameter("ordering", str, enum=["fecha", "-fecha"]), OpenApiParameter("page", int), OpenApiParameter("page_size", int),
]


class MisCitasView(BasePortalPacienteView):
    serializer_class = CitaPortalSerializer

    @extend_schema(tags=["Portal del paciente"], parameters=[*PARAMETROS_COMUNES, OpenApiParameter("estado", str)], responses={200: RespuestaCitasPortalSerializer, **ERRORES}, description="Lista paginada y de solo lectura de las citas propias.")
    def get(self, request):
        entrada = FiltrosCitasPortalSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        queryset = obtener_citas_portal(paciente=self.paciente(), clinica=request.user.clinica, filtros=entrada.validated_data)
        pagina = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(pagina, many=True).data)


class MisConsultasView(BasePortalPacienteView):
    serializer_class = ConsultaPortalSerializer

    @extend_schema(tags=["Portal del paciente"], parameters=PARAMETROS_COMUNES, responses={200: RespuestaConsultasPortalSerializer, **ERRORES}, description="Lista paginada de consultas y resúmenes de recetas propias.")
    def get(self, request):
        entrada = FiltrosFechasPortalSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        queryset = obtener_consultas_portal(paciente=self.paciente(), clinica=request.user.clinica, filtros=entrada.validated_data)
        pagina = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(pagina, many=True).data)


class MiRecetaDetalleView(BasePortalPacienteView):
    serializer_class = RecetaDetallePortalSerializer

    @extend_schema(tags=["Portal del paciente"], responses={200: RecetaDetallePortalSerializer, **ERRORES}, description="Devuelve una receta propia y sus medicamentos, sin permitir escritura.")
    def get(self, request, pk):
        receta = obtener_receta_portal(receta_id=pk, paciente=self.paciente(), clinica=request.user.clinica)
        return Response(self.get_serializer(receta).data)
