"""Vistas de personal, especialidades, médicos y horarios."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.core.identidad import (
    ConsultaIdentidadSerializer,
    IdentidadCompartidaSerializer,
    respuesta_identidad,
)
from apps.core.permissions import (
    EsAdminClinica,
    EsAdminClinicaOMedico,
    PuedeConsultarRecursosCita,
    TieneClinica,
    TieneSuscripcionVigente,
    tiene_rol,
)
from apps.core.querysets import queryset_tenant
from apps.core.seed_data import ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA
from apps.pacientes.models import Paciente
from apps.seguridad.cuentas_serializers import (
    BuscarCuentasElegiblesSerializer,
    CrearCuentaPersonalSerializer,
)
from apps.seguridad.cuentas_services import (
    crear_cuenta_para_personal,
    cuentas_elegibles_para_personal,
)
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
    finalizar_relacion_laboral,
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
            "usuario_ya_vinculado, rol_obligatorio_no_disponible, "
            "rol_requerido_por_personal."
        )
    ),
}


def _es_admin_clinica(usuario):
    return tiene_rol(usuario, ROL_ADMIN_CLINICA)


def _es_recepcionista(usuario):
    return tiene_rol(usuario, ROL_RECEPCIONISTA)


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
        qs = queryset_tenant(Personal, self.request).select_related(
            "usuario"
        ).prefetch_related("usuario__roles_asignados__rol")
        cargo = self.request.query_params.get("cargo")
        if cargo:
            qs = qs.filter(cargo=cargo.upper())
        estado = self.request.query_params.get("estado")
        if estado is not None:
            qs = qs.filter(estado=estado.lower() in ("1", "true", "si"))
        return qs

    @extend_schema(
        parameters=[ConsultaIdentidadSerializer],
        responses={200: IdentidadCompartidaSerializer},
        description=(
            "Busca en Pacientes la identidad de la misma clínica con CI exacta."
        ),
    )
    @action(detail=False, methods=["get"], url_path="identidad-por-ci")
    def identidad_por_ci(self, request):
        parametros = ConsultaIdentidadSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        paciente = (
            Paciente.all_objects.select_related("usuario")
            .filter(
                clinica=request.user.clinica,
                ci=parametros.validated_data["ci"],
            )
            .first()
        )
        return Response(respuesta_identidad(paciente, "PACIENTE"))

    def create(self, request, *args, **kwargs):
        if "usuario" in request.data:
            from apps.core.api_exceptions import DatosInvalidos

            raise DatosInvalidos(
                "La cuenta se crea o vincula desde las acciones de cuenta.",
                codigo="datos_invalidos",
            )
        serializer = PersonalSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        personal = crear_personal(
            request.user.clinica, dict(serializer.validated_data)
        )
        return Response(
            PersonalSerializer(personal).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        if "usuario" in request.data:
            from apps.core.api_exceptions import DatosInvalidos

            raise DatosInvalidos(
                "La cuenta se administra desde las acciones de cuenta.",
                codigo="datos_invalidos",
            )
        parcial = kwargs.pop("partial", False)
        personal = self.get_object()
        serializer = PersonalSerializer(
            personal,
            data=request.data,
            partial=parcial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        personal = actualizar_personal(
            personal, dict(serializer.validated_data)
        )
        return Response(PersonalSerializer(personal).data)

    def destroy(self, request, *args, **kwargs):
        finalizar_relacion_laboral(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=UsuarioSerializer,
        responses={200: PersonalSerializer, **ERRORES_COMUNES},
        description=(
            "Vincula una cuenta verificada por CI. El vínculo es permanente; "
            "la baja laboral se realiza con DELETE."
        ),
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

    @extend_schema(
        request=CrearCuentaPersonalSerializer,
        responses={201: PersonalSerializer, **ERRORES_COMUNES},
        description="Crea una cuenta y la vincula atómicamente al personal.",
    )
    @action(detail=True, methods=["post"], url_path="crear-cuenta")
    def crear_cuenta(self, request, pk=None):
        entrada = CrearCuentaPersonalSerializer(
            data=request.data, context={"request": request}
        )
        entrada.is_valid(raise_exception=True)
        datos = dict(entrada.validated_data)
        roles = datos.pop("roles", [])
        personal = crear_cuenta_para_personal(
            clinica=request.user.clinica,
            personal_id=pk,
            datos=datos,
            roles=roles,
        )
        return Response(PersonalSerializer(personal).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[BuscarCuentasElegiblesSerializer],
        responses={200: UsuarioSerializer(many=True), **ERRORES_COMUNES},
        description="Lista cuentas verificables por un Paciente con la misma CI.",
    )
    @action(detail=True, methods=["get"], url_path="cuentas-elegibles")
    def cuentas_elegibles(self, request, pk=None):
        parametros = BuscarCuentasElegiblesSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        personal = Personal.all_objects.filter(
            pk=pk, clinica=request.user.clinica
        ).first()
        if personal is None:
            from apps.core.api_exceptions import RecursoNoEncontrado

            raise RecursoNoEncontrado("Personal no encontrado.")
        queryset = cuentas_elegibles_para_personal(
            clinica=request.user.clinica,
            personal=personal,
            search=parametros.validated_data.get("search", "").strip(),
        )
        pagina = self.paginate_queryset(queryset)
        serializer = UsuarioSerializer(pagina, many=True)
        return self.get_paginated_response(serializer.data)


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
                PuedeConsultarRecursosCita(),
            ]
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            EsAdminClinica(),
        ]

    def get_queryset(self):
        qs = queryset_tenant(Especialidad, self.request)
        usuario = self.request.user
        if not getattr(usuario, "is_authenticated", False):
            return qs.none()
        if _es_admin_clinica(usuario) or _es_recepcionista(usuario):
            return qs
        medico = _medico_del_usuario(usuario)
        if medico is None:
            return qs.none()
        return qs.filter(
            Q(pk=medico.especialidad_id)
            | Q(medicos_especialistas=medico)
        ).distinct()

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
        if (
            Medico.all_objects.filter(especialidad=especialidad).exists()
            or Medico.all_objects.filter(
                especialidades=especialidad
            ).exists()
        ):
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
                PuedeConsultarRecursosCita(),
            ]
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            EsAdminClinica(),
        ]

    def get_queryset(self):
        qs = queryset_tenant(Medico, self.request).prefetch_related(
            "especialidades"
        )
        usuario = self.request.user
        if not getattr(usuario, "is_authenticated", False):
            return qs
        if _es_admin_clinica(usuario) or _es_recepcionista(usuario):
            especialidad = self.request.query_params.get("especialidad")
            if especialidad:
                qs = qs.filter(
                    Q(especialidad_id=especialidad)
                    | Q(especialidades__id=especialidad)
                ).distinct()
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
