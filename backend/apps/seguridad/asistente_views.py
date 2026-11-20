"""Endpoint REST del Asistente Guía interactivo impulsado por Ollama."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.response import Response

from apps.core.permissions import TieneClinica

from .asistente_serializers import (
    AsistenteConsultaSerializer,
    AsistenteRespuestaSerializer,
)
from .asistente_services import consultar_asistente_guia


class AsistenteConsultarView(generics.GenericAPIView):
    serializer_class = AsistenteConsultaSerializer
    permission_classes = (TieneClinica,)

    @extend_schema(
        tags=["Asistente Guía"],
        description=(
            "Consulta al Asistente Guía interactivo (Ollama) filtrando "
            "el manual y los identificadores UI según los roles activos del usuario."
        ),
        request=AsistenteConsultaSerializer,
        responses={
            200: AsistenteRespuestaSerializer,
            400: OpenApiResponse(description="Consulta vacía o inválida."),
            401: OpenApiResponse(description="No autenticado."),
            403: OpenApiResponse(description="Sin clínica o sin rol activo."),
            503: OpenApiResponse(description="Ollama no disponible o tiempo excedido."),
        },
    )
    def post(self, request):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        resultado = consultar_asistente_guia(
            usuario=request.user,
            consulta=entrada.validated_data["consulta"],
            ruta_actual=entrada.validated_data.get("ruta_actual") or "/",
        )
        return Response(AsistenteRespuestaSerializer(resultado).data)
