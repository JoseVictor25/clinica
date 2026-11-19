"""Endpoints REST de estudios médicos y descarga proxied desde Supabase Storage."""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import (
    EsMedico,
    PuedeAccederEstudiosMedicos,
    TieneClinica,
    TieneSuscripcionVigente,
)

from .estudios_serializers import (
    EstudioMedicoActualizarSerializer,
    EstudioMedicoCrearSerializer,
    EstudioMedicoRevisarSerializer,
    EstudioMedicoSerializer,
)
from .estudios_services import (
    actualizar_estudio,
    crear_estudio,
    descargar_archivo_estudio,
    eliminar_estudio,
    listar_estudios,
    obtener_estudio,
    revisar_estudio,
)
from .models import EstadoEstudio, EstudioMedico, FormatoEstudio


def _parsear_entero_opcional(valor, nombre):
    if valor in (None, ""):
        return None
    try:
        entero = int(valor)
        if entero <= 0:
            raise ValueError
        return entero
    except (TypeError, ValueError) as exc:
        raise ValidationError({nombre: ["Debe ser un entero positivo."]}) from exc


@extend_schema_view(
    list=extend_schema(
        tags=["Estudios médicos"],
        parameters=[
            OpenApiParameter("cita_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("paciente_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("consulta_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("estado", str, required=False, enum=EstadoEstudio.values),
            OpenApiParameter("formato", str, required=False, enum=FormatoEstudio.values),
        ],
    ),
    retrieve=extend_schema(tags=["Estudios médicos"]),
    create=extend_schema(
        tags=["Estudios médicos"],
        request=EstudioMedicoCrearSerializer,
        responses={201: EstudioMedicoSerializer},
    ),
    partial_update=extend_schema(
        tags=["Estudios médicos"],
        request=EstudioMedicoActualizarSerializer,
        responses={200: EstudioMedicoSerializer},
    ),
    destroy=extend_schema(tags=["Estudios médicos"]),
)
class EstudioMedicoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EstudioMedico.all_objects.none()
    serializer_class = EstudioMedicoSerializer
    permission_classes = (TieneClinica, TieneSuscripcionVigente, PuedeAccederEstudiosMedicos)
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        params = self.request.query_params
        estado = params.get("estado")
        if estado and estado not in EstadoEstudio.values:
            raise ValidationError({"estado": ["Estado de estudio inválido."]})
        formato = params.get("formato")
        if formato and formato not in FormatoEstudio.values:
            raise ValidationError({"formato": ["Formato de estudio inválido."]})

        filtros = {
            "cita_id": _parsear_entero_opcional(params.get("cita_id"), "cita_id"),
            "paciente_id": _parsear_entero_opcional(params.get("paciente_id"), "paciente_id"),
            "consulta_id": _parsear_entero_opcional(params.get("consulta_id"), "consulta_id"),
            "estado": estado or None,
            "formato": formato or None,
        }
        return listar_estudios(
            usuario=self.request.user,
            clinica=self.request.user.clinica,
            filtros=filtros,
        )

    def get_object(self):
        return obtener_estudio(
            usuario=self.request.user,
            clinica=self.request.user.clinica,
            estudio_id=self.kwargs["pk"],
        )

    def create(self, request, *args, **kwargs):
        entrada = EstudioMedicoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estudio = crear_estudio(
            usuario=request.user,
            clinica=request.user.clinica,
            datos=entrada.validated_data,
        )
        return Response(
            EstudioMedicoSerializer(estudio).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        entrada = EstudioMedicoActualizarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estudio = actualizar_estudio(
            usuario=request.user,
            clinica=request.user.clinica,
            estudio_id=kwargs["pk"],
            datos=entrada.validated_data,
        )
        return Response(EstudioMedicoSerializer(estudio).data)

    def destroy(self, request, *args, **kwargs):
        eliminar_estudio(
            usuario=request.user,
            clinica=request.user.clinica,
            estudio_id=kwargs["pk"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Estudios médicos"],
        request=EstudioMedicoRevisarSerializer,
        responses={200: EstudioMedicoSerializer},
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="revisar",
        permission_classes=(TieneClinica, TieneSuscripcionVigente, EsMedico),
    )
    def revisar(self, request, pk=None):
        entrada = EstudioMedicoRevisarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estudio = revisar_estudio(
            usuario=request.user,
            clinica=request.user.clinica,
            estudio_id=pk,
            datos=entrada.validated_data,
        )
        return Response(EstudioMedicoSerializer(estudio).data)

    @extend_schema(
        tags=["Estudios médicos"],
        responses={200: OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"], url_path="archivo")
    def archivo(self, request, pk=None):
        estudio, contenido, content_type = descargar_archivo_estudio(
            usuario=request.user,
            clinica=request.user.clinica,
            estudio_id=pk,
        )
        disposicion = "attachment" if request.query_params.get("download") == "1" else "inline"
        nombre_seguro = estudio.nombre_archivo.replace('"', "")
        respuesta = HttpResponse(contenido, content_type=content_type)
        respuesta["Content-Disposition"] = f'{disposicion}; filename="{nombre_seguro}"'
        return respuesta
