from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api_exceptions import Conflicto
from apps.core.permissions import TieneClinica, TieneSuscripcionVigente

from .models import DispositivoPush, Notificacion
from .serializers import DispositivoPushSerializer, NotificacionSerializer


class NotificacionesView(APIView):
    permission_classes = (IsAuthenticated, TieneClinica, TieneSuscripcionVigente)

    @extend_schema(
        tags=["Notificaciones"],
        responses={200: NotificacionSerializer(many=True)},
        description="Lista las últimas 50 notificaciones de la cuenta y su total no leído.",
    )
    def get(self, request):
        queryset = Notificacion.objects.filter(usuario=request.user).order_by(
            "-creada_en"
        )
        total_no_leidas = queryset.filter(leida_en__isnull=True).count()
        resultados = NotificacionSerializer(queryset[:50], many=True).data
        return Response(
            {
                "codigo": "notificaciones_listadas",
                "no_leidas": total_no_leidas,
                "resultados": resultados,
            }
        )

    @extend_schema(
        tags=["Notificaciones"],
        responses={200: OpenApiResponse(description="Notificaciones marcadas como leídas.")},
        description="Marca todas las notificaciones de la cuenta autenticada como leídas.",
    )
    def post(self, request):
        ahora = timezone.now()
        actualizadas = Notificacion.objects.filter(
            usuario=request.user,
            leida_en__isnull=True,
        ).update(leida_en=ahora)
        return Response(
            {
                "codigo": "notificaciones_leidas",
                "mensaje": "Notificaciones marcadas como leídas.",
                "actualizadas": actualizadas,
            }
        )


class NotificacionLeerView(APIView):
    permission_classes = (IsAuthenticated, TieneClinica, TieneSuscripcionVigente)

    @extend_schema(
        tags=["Notificaciones"],
        responses={200: OpenApiResponse(description="Notificación marcada como leída.")},
        description="Marca como leída una notificación perteneciente a la cuenta autenticada.",
    )
    def post(self, request, pk):
        notificacion = get_object_or_404(
            Notificacion.objects.filter(usuario=request.user),
            pk=pk,
        )
        if notificacion.leida_en is None:
            notificacion.leida_en = timezone.now()
            notificacion.save(update_fields=("leida_en",))
        return Response({"codigo": "notificacion_leida", "mensaje": "Notificación marcada como leída."})


class DispositivoPushView(APIView):
    permission_classes = (IsAuthenticated, TieneClinica, TieneSuscripcionVigente)

    @extend_schema(
        tags=["Notificaciones"],
        request=DispositivoPushSerializer,
        responses={200: OpenApiResponse(description="Dispositivo registrado.")},
        description=(
            "Asocia el identificador de instalación FCM con la cuenta JWT actual. "
            "El mismo usuario puede actualizar la plataforma del dispositivo."
        ),
    )
    def post(self, request):
        entrada = DispositivoPushSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        token = entrada.validated_data["token"]
        try:
            with transaction.atomic():
                dispositivo = (
                    DispositivoPush.all_objects.select_for_update()
                    .filter(token=token)
                    .first()
                )
                if dispositivo and dispositivo.usuario_id != request.user.pk:
                    raise Conflicto(
                        "Este dispositivo ya está vinculado a otra cuenta.",
                        codigo="dispositivo_vinculado",
                    )
                if dispositivo is None:
                    DispositivoPush.all_objects.create(
                        usuario=request.user,
                        token=token,
                        plataforma=entrada.validated_data["plataforma"],
                    )
                else:
                    dispositivo.plataforma = entrada.validated_data["plataforma"]
                    dispositivo.save(update_fields=("plataforma", "actualizado_en"))
        except IntegrityError as exc:
            raise Conflicto(
                "No se pudo asociar este dispositivo a la cuenta.",
                codigo="dispositivo_vinculado",
            ) from exc
        return Response(
            {"codigo": "dispositivo_registrado", "mensaje": "Dispositivo registrado."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Notificaciones"],
        request=DispositivoPushSerializer,
        responses={204: OpenApiResponse(description="Dispositivo eliminado.")},
        description="Elimina el dispositivo registrado de la cuenta autenticada.",
    )
    def delete(self, request):
        entrada = DispositivoPushSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        DispositivoPush.all_objects.filter(
            usuario=request.user,
            token=entrada.validated_data["token"],
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
