"""Vistas de personal, especialidades, médicos y horarios."""

from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.core.permissions import (
    EsAdminClinica,
    EsAdminClinicaOMedico,
    TieneClinica,
    TieneSuscripcionVigente,
    tiene_rol,
)
from apps.core.querysets import queryset_tenant
from apps.core.seed_data import ROL_ADMIN_CLINICA
from apps.seguridad.serializers import UsuarioSerializer

from .models import Especialidad, HorarioAtencion, Medico, Personal
from .serializers import (
    EspecialidadSerializer,
    HorarioAtencionSerializer,
    MedicoSerializer,
    PersonalSerializer,
)
from .services import (
    actualizar_especialidad,
    actualizar_horario,
    actualizar_medico,
    actualizar_personal,
    crear_especialidad,
    crear_horario,
    crear_medico,
    crear_personal,
    vincular_usuario,
)

ERRORES_COMUNES = {
    400: OpenApiResponse(
        description="Datos inválidos: datos_invalidos, horario_invalido."
    ),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description=(
            "Sin permiso (permiso_denegado), suscripción vencida "
            "(suscripcion_vencida), clínica inactiva (clinica_inactiva) "
            "o médico no vinculado (medico_no_vinculado)."
        )
    ),
    404: OpenApiResponse(
        description="No encontrado o de otra clínica (no_encontrado)."
    ),
    409: OpenApiResponse(
        description=(
            "Conflicto de negocio: ci_duplicada, personal_ya_es_medico, "
            "colegiatura_duplicada, especialidad_duplicada, "
            "especialidad_en_uso, horario_solapado, personal_con_medico, "
            "usuario_ya_vinculado."
        )
    ),
}


def _es_admin_clinica(usuario):
    return tiene_rol(usuario, ROL_ADMIN_CLINICA)


def _personal_del_usuario(usuario):
    try:
        return usuario.personal
    except ObjectDoesNotExist:
        return None


def _medico_del_usuario(usuario):
    personal = _personal_del_usuario(usuario)
    if personal is None:
        return None
    try:
        return personal.medico
    except ObjectDoesNotExist:
        return None


class PersonalViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalSerializer
    permission_classes = [
        TieneClinica,
        TieneSuscripcionVigente,
        EsAdminClinica,
    ]
    search_fields = ("ci", "nombre", "apellido", "telefono")
    ordering_fields = ("apellido", "nombre", "fecha_ingreso", "estado")
    ordering = ("apellido", "nombre")

    def get_queryset(self):
        qs = queryset_tenant(Personal, self.request)
        cargo = self.request.query_params.get("cargo")
        if cargo:
            qs = qs.filter(cargo=cargo.upper())
        estado = self.request.query_params.get("estado")
        if estado is not None:
            qs = qs.filter(estado=estado.lower() in ("1", "true", "si"))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = PersonalSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        usuario = datos.pop("usuario", None)
        personal = crear_personal(request.user.clinica, datos)
        if usuario is not None:
            vincular_usuario(personal, usuario)
        return Response(
            PersonalSerializer(personal).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        personal = self.get_object()
        serializer = PersonalSerializer(
            personal,
            data=request.data,
            partial=parcial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        usuario = datos.pop("usuario", None)
        personal = actualizar_personal(personal, datos)
        if "usuario" in request.data or usuario is not None:
            vincular_usuario(personal, usuario)
        return Response(PersonalSerializer(personal).data)

    def destroy(self, request, *args, **kwargs):
        personal = self.get_object()
        if Medico.all_objects.filter(personal=personal).exists():
            from apps.core.api_exceptions import Conflicto

            raise Conflicto(
                "El personal tiene un médico asociado y no se puede eliminar.",
                codigo="personal_con_medico",
            )
        personal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=UsuarioSerializer,
        responses={200: PersonalSerializer, **ERRORES_COMUNES},
        description="Vincula o desvincula un usuario de la misma clínica.",
    )
    @action(detail=True, methods=["post"], url_path="vincular-usuario")
    def vincular_usuario(self, request, pk=None):
        personal = self.get_object()
        usuario_id = request.data.get("usuario_id")
        if usuario_id is None:
            return Response(
                PersonalSerializer(
                    vincular_usuario(personal, None)
                ).data
            )
        from apps.seguridad.models import Usuario

        usuario = Usuario.tenant_objects.filter(pk=usuario_id).first()
        if usuario is None:
            from apps.core.api_exceptions import RecursoNoEncontrado

            raise RecursoNoEncontrado("Usuario no encontrado.")
        return Response(
            PersonalSerializer(vincular_usuario(personal, usuario)).data
        )


class EspecialidadViewSet(viewsets.ModelViewSet):
    serializer_class = EspecialidadSerializer
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "estado")
    ordering = ("nombre",)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [
                TieneClinica(),
                TieneSuscripcionVigente(),
                EsAdminClinicaOMedico(),
            ]
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            EsAdminClinica(),
        ]

    def get_queryset(self):
        return queryset_tenant(Especialidad, self.request)

    def create(self, request, *args, **kwargs):
        serializer = EspecialidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        especialidad = crear_especialidad(
            request.user.clinica, dict(serializer.validated_data)
        )
        return Response(
            EspecialidadSerializer(especialidad).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        especialidad = self.get_object()
        serializer = EspecialidadSerializer(
            especialidad, data=request.data, partial=parcial
        )
        serializer.is_valid(raise_exception=True)
        especialidad = actualizar_especialidad(
            especialidad, dict(serializer.validated_data)
        )
        return Response(EspecialidadSerializer(especialidad).data)

    def destroy(self, request, *args, **kwargs):
        especialidad = self.get_object()
        if Medico.all_objects.filter(especialidad=especialidad).exists():
            from apps.core.api_exceptions import Conflicto

            raise Conflicto(
                "La especialidad está en uso por un médico.",
                codigo="especialidad_en_uso",
            )
        especialidad.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MedicoViewSet(viewsets.ModelViewSet):
    serializer_class = MedicoSerializer
    search_fields = (
        "personal__nombre",
        "personal__apellido",
        "numero_colegiatura",
    )
    ordering_fields = ("numero_colegiatura", "estado")
    ordering = ("personal__apellido", "personal__nombre")

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [
                TieneClinica(),
                TieneSuscripcionVigente(),
                EsAdminClinicaOMedico(),
            ]
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            EsAdminClinica(),
        ]

    def get_queryset(self):
        qs = queryset_tenant(Medico, self.request)
        usuario = self.request.user
        if not getattr(usuario, "is_authenticated", False):
            return qs
        if _es_admin_clinica(usuario):
            especialidad = self.request.query_params.get("especialidad")
            if especialidad:
                qs = qs.filter(especialidad_id=especialidad)
            return qs
        # Médico sin Personal/Médico vinculado: lista vacía, nunca 500.
        return qs.filter(personal__usuario=usuario)

    def create(self, request, *args, **kwargs):
        serializer = MedicoSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        medico = crear_medico(
            request.user.clinica, dict(serializer.validated_data)
        )
        return Response(
            MedicoSerializer(medico).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        medico = self.get_object()
        serializer = MedicoSerializer(
            medico,
            data=request.data,
            partial=parcial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        medico = actualizar_medico(medico, dict(serializer.validated_data))
        return Response(MedicoSerializer(medico).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HorarioAtencionViewSet(viewsets.ModelViewSet):
    serializer_class = HorarioAtencionSerializer
    ordering_fields = ("dia_semana", "hora_inicio", "hora_fin")
    ordering = ("dia_semana", "hora_inicio")

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [
                TieneClinica(),
                TieneSuscripcionVigente(),
                EsAdminClinicaOMedico(),
            ]
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            EsAdminClinicaOMedico(),
        ]

    def get_queryset(self):
        qs = queryset_tenant(HorarioAtencion, self.request)
        usuario = self.request.user
        if not getattr(usuario, "is_authenticated", False):
            return qs
        if _es_admin_clinica(usuario):
            medico = self.request.query_params.get("medico")
            if medico:
                qs = qs.filter(medico_id=medico)
            dia = self.request.query_params.get("dia_semana")
            if dia is not None:
                qs = qs.filter(dia_semana=dia)
            return qs
        return qs.filter(medico__personal__usuario=usuario)

    def create(self, request, *args, **kwargs):
        serializer = HorarioAtencionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        if _es_admin_clinica(request.user):
            medico = datos.pop("medico", None)
            if medico is None:
                from apps.core.api_exceptions import DatosInvalidos

                raise DatosInvalidos(
                    "El médico es obligatorio para crear un horario.",
                    codigo="medico_requerido",
                )
        else:
            medico = _medico_del_usuario(request.user)
            if medico is None:
                from apps.core.api_exceptions import PermisoDenegado

                raise PermisoDenegado(
                    "El usuario no tiene un registro de médico vinculado.",
                    codigo="medico_no_vinculado",
                )
            datos.pop("medico", None)
        horario = crear_horario(medico, datos)
        return Response(
            HorarioAtencionSerializer(horario).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        horario = self.get_object()
        serializer = HorarioAtencionSerializer(
            horario,
            data=request.data,
            partial=parcial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        if not _es_admin_clinica(request.user):
            datos["medico"] = horario.medico
        horario = actualizar_horario(horario, datos)
        return Response(HorarioAtencionSerializer(horario).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
