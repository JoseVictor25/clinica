"""Vistas de clínicas, planes y suscripciones."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import (
    EsAdminClinica,
    EsAdminSistema,
    EsAdminSistemaOAdminClinica,
    TieneSuscripcionVigente,
)
from apps.core.querysets import queryset_tenant

from .models import Clinica, PlanSuscripcion, Suscripcion
from .serializers import (
    CambiarPlanSerializer,
    ClinicaCreateSerializer,
    ClinicaSerializer,
    PlanSuscripcionSerializer,
    RenovarSuscripcionSerializer,
    SuscripcionCreateSerializer,
    SuscripcionSerializer,
)
from .services import (
    cambiar_plan,
    cancelar_suscripcion,
    contratar_suscripcion,
    registrar_clinica,
    renovar_suscripcion,
)

ERRORES_COMUNES = {
    400: OpenApiResponse(
        description="Datos inválidos: datos_invalidos, fechas_invalidas."
    ),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description=(
            "Sin permiso (permiso_denegado) o clínica inactiva "
            "(clinica_inactiva)."
        )
    ),
    404: OpenApiResponse(
        description="No encontrado o de otra clínica (no_encontrado)."
    ),
    409: OpenApiResponse(
        description=(
            "Conflicto de negocio: nit_duplicado, usuario_duplicado, "
            "email_duplicado, clinica_duplicada, plan_inactivo, "
            "limite_usuarios, suscripcion_activa, suscripcion_no_vigente, "
            "suscripcion_no_activa, fecha_fin_invalida."
        )
    ),
}


class ClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicaSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [
                TieneSuscripcionVigente(),
                EsAdminSistemaOAdminClinica(),
            ]
        return [EsAdminSistema()]

    def get_queryset(self):
        usuario = self.request.user
        if getattr(usuario, "is_superuser", False) and not getattr(
            usuario, "clinica_id", None
        ):
            return Clinica.objects.all()
        return Clinica.objects.filter(pk=getattr(usuario, "clinica_id", None))

    @extend_schema(
        request=ClinicaCreateSerializer,
        responses={201: ClinicaSerializer, **ERRORES_COMUNES},
        description="Registra una clínica y provisiona roles, especialidades y primer administrador.",
    )
    def create(self, request, *args, **kwargs):
        serializer = ClinicaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        admin = datos.pop("admin")
        clinica = registrar_clinica(datos, admin)
        return Response(
            ClinicaSerializer(clinica).data, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        clinica = self.get_object()
        clinica.estado = False
        clinica.save(update_fields=["estado"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlanSuscripcionViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSuscripcionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [EsAdminSistemaOAdminClinica()]
        return [EsAdminSistema()]

    def get_queryset(self):
        qs = PlanSuscripcion.objects.all()
        activo = self.request.query_params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() in ("1", "true", "si"))
        return qs

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        plan.activo = False
        plan.save(update_fields=["activo"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuscripcionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SuscripcionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EsAdminSistemaOAdminClinica()]
        return [EsAdminClinica()]

    def get_queryset(self):
        qs = queryset_tenant(Suscripcion, self.request)
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado.upper())
        return qs

    @extend_schema(
        request=SuscripcionCreateSerializer,
        responses={201: SuscripcionSerializer, **ERRORES_COMUNES},
        description="Contrata un plan para la clínica autenticada.",
    )
    def create(self, request, *args, **kwargs):
        serializer = SuscripcionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suscripcion = contratar_suscripcion(
            request.user.clinica,
            serializer.validated_data["plan"],
            serializer.validated_data["fecha_inicio"],
            serializer.validated_data["fecha_fin"],
        )
        return Response(
            SuscripcionSerializer(suscripcion).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=RenovarSuscripcionSerializer,
        responses={200: SuscripcionSerializer, **ERRORES_COMUNES},
        description="Extiende la fecha de fin de la suscripción vigente.",
    )
    @action(detail=True, methods=["post"], url_path="renovar")
    def renovar(self, request, pk=None):
        suscripcion = self.get_object()
        serializer = RenovarSuscripcionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suscripcion = renovar_suscripcion(
            suscripcion, serializer.validated_data["nueva_fecha_fin"]
        )
        return Response(SuscripcionSerializer(suscripcion).data)

    @extend_schema(
        request=CambiarPlanSerializer,
        responses={200: SuscripcionSerializer, **ERRORES_COMUNES},
        description="Cancela la suscripción actual y crea una nueva con otro plan.",
    )
    @action(detail=True, methods=["post"], url_path="cambiar-plan")
    def cambiar_plan(self, request, pk=None):
        suscripcion = self.get_object()
        serializer = CambiarPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nueva = cambiar_plan(
            suscripcion,
            serializer.validated_data["plan"],
            serializer.validated_data["fecha_inicio"],
            serializer.validated_data["fecha_fin"],
        )
        return Response(SuscripcionSerializer(nueva).data)

    @extend_schema(
        request=None,
        responses={200: SuscripcionSerializer, **ERRORES_COMUNES},
        description="Marca la suscripción como CANCELADA.",
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        suscripcion = cancelar_suscripcion(self.get_object())
        return Response(SuscripcionSerializer(suscripcion).data)
