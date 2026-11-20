"""API REST de pacientes."""

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.core.identidad import (
    ConsultaIdentidadSerializer,
    IdentidadCompartidaSerializer,
    respuesta_identidad,
)
from apps.core.permissions import (
    EsAdminClinicaORecepcionista,
    EsAdminClinica,
    EsMedico,
    PuedeConsultarAlergias,
    PuedeConsultarPacientes,
    PuedeConsultarEnfermedades,
    TieneClinica,
    TieneSuscripcionVigente,
)
from apps.core.querysets import queryset_tenant
from .acceso import pacientes_accesibles_para_usuario
from apps.personal.models import Personal
from apps.seguridad.cuentas_serializers import (
    BuscarCuentasElegiblesSerializer,
    CrearCuentaPacienteSerializer,
)
from apps.seguridad.cuentas_services import (
    crear_cuenta_para_paciente,
    cuentas_elegibles_para_paciente,
)
from apps.seguridad.serializers import UsuarioSerializer

from .models import (
    Alergia,
    Enfermedad,
    Paciente,
    Severidad,
    Sexo,
    TipoAlergia,
    TipoEnfermedad,
)
from .serializers import (
    AlergiaSerializer,
    ConsultaHistorialSerializer,
    EnfermedadSerializer,
    HistorialConsultasParametrosSerializer,
    HistorialConsultasRespuestaSerializer,
    PacienteHistorialSerializer,
    PacienteSerializer,
)
from .services import (
    actualizar_alergia,
    actualizar_enfermedad,
    actualizar_paciente,
    crear_alergia,
    crear_enfermedad,
    crear_paciente,
    desactivar_paciente,
    obtener_historia_paciente,
    obtener_historial_consultas,
)
from .vinculacion_serializers import (
    VincularUsuarioPacienteRespuestaSerializer,
    VincularUsuarioPacienteSerializer,
)
from .vinculacion_services import vincular_usuario_paciente

ERRORES = {
    400: OpenApiResponse(
        description="Datos inválidos o fecha_nacimiento_invalida."
    ),
    401: OpenApiResponse(description="No autenticado."),
    403: OpenApiResponse(
        description=(
            "Rol no permitido, clínica inactiva o suscripción vencida."
        )
    ),
    404: OpenApiResponse(
        description="Paciente inexistente o de otra clínica."
    ),
    409: OpenApiResponse(description="CI duplicada (ci_duplicada)."),
}

ERRORES_HISTORIAL = {
    400: OpenApiResponse(description="Filtros inválidos (datos_invalidos)."),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description=(
            "Rol no permitido, clínica inactiva o suscripción vencida "
            "(permiso_denegado, clinica_inactiva, suscripcion_vencida)."
        )
    ),
    404: OpenApiResponse(
        description="Paciente o médico de filtro inexistente o de otro tenant (no_encontrado)."
    ),
    409: OpenApiResponse(
        description="Paciente inactivo o sin historia (paciente_inactivo, historia_no_disponible)."
    ),
}


class HistorialConsultasPacienteView(generics.GenericAPIView):
    """Historial clínico consolidado, paginado y de solo lectura."""

    permission_classes = (TieneClinica, TieneSuscripcionVigente, EsMedico)
    serializer_class = ConsultaHistorialSerializer

    @extend_schema(
        tags=["Historial clínico"],
        description=(
            "Devuelve el historial cronológico de consultas de un paciente activo "
            "de la clínica del médico autenticado, incluidas consultas realizadas "
            "por otros médicos del mismo tenant, citas opcionales, recetas y "
            "medicamentos. Es de solo lectura y no actualiza la historia. "
            "puede_ver_detalle es calculado y solo es verdadero para recetas del "
            "médico autenticado; las advertencias de alergias permanecen en el "
            "detalle protegido de S2-10. Evita N+1 mediante precargas tenant-safe."
        ),
        parameters=[
            OpenApiParameter("paciente_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("fecha_desde", OpenApiTypes.DATE),
            OpenApiParameter("fecha_hasta", OpenApiTypes.DATE),
            OpenApiParameter("medico_id", OpenApiTypes.INT),
            OpenApiParameter("ordering", str, enum=["fecha", "-fecha"]),
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses={200: HistorialConsultasRespuestaSerializer, **ERRORES_HISTORIAL},
    )
    def get(self, request, paciente_id):
        parametros = HistorialConsultasParametrosSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        paciente, medico, consultas = obtener_historial_consultas(
            usuario=request.user,
            clinica=request.user.clinica,
            paciente_id=paciente_id,
            filtros=parametros.validated_data,
        )
        pagina = self.paginate_queryset(consultas)
        contexto = {"medico_autenticado_id": medico.pk, "request": request}
        resultados = ConsultaHistorialSerializer(
            pagina if pagina is not None else consultas,
            many=True,
            context=contexto,
        ).data
        paciente_data = PacienteHistorialSerializer(paciente).data
        if pagina is not None:
            respuesta = self.get_paginated_response(resultados)
            respuesta.data = {"paciente": paciente_data, **respuesta.data}
            return respuesta
        return Response({
            "paciente": paciente_data,
            "count": len(resultados),
            "next": None,
            "previous": None,
            "results": resultados,
        })


@extend_schema_view(
    list=extend_schema(
        tags=["Pacientes"],
        parameters=[
            OpenApiParameter(
                "search",
                str,
                description=(
                    "Busca por CI, nombre, apellido, teléfono o email."
                ),
            ),
            OpenApiParameter("estado", bool),
            OpenApiParameter("sexo", str, enum=Sexo.values),
            OpenApiParameter(
                "ordering",
                str,
                description=(
                    "apellido, nombre, fecha_nacimiento o estado"
                ),
            ),
        ],
        responses={200: PacienteSerializer(many=True), **ERRORES},
    ),
    create=extend_schema(
        tags=["Pacientes"],
        description=(
            "Registra un paciente y crea automáticamente su historia "
            "clínica en una única transacción. Si cualquiera de las dos "
            "creaciones falla, la operación completa se revierte. La "
            "respuesta conserva únicamente el contrato administrativo "
            "del paciente y no expone datos de la historia clínica."
        ),
        responses={201: PacienteSerializer, **ERRORES},
    ),
    retrieve=extend_schema(
        tags=["Pacientes"],
        responses={200: PacienteSerializer, **ERRORES},
    ),
    partial_update=extend_schema(
        tags=["Pacientes"],
        responses={200: PacienteSerializer, **ERRORES},
    ),
    destroy=extend_schema(
        tags=["Pacientes"],
        responses={204: None, **ERRORES},
    ),
)
class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]
    search_fields = ("ci", "nombre", "apellido", "telefono", "email")
    ordering_fields = (
        "apellido",
        "nombre",
        "fecha_nacimiento",
        "estado",
    )
    ordering = ("apellido", "nombre")

    def get_permissions(self):
        acciones_cuenta = {"vincular_usuario", "crear_cuenta", "cuentas_elegibles"}
        permiso_rol = EsAdminClinica if self.action in acciones_cuenta else (
            PuedeConsultarPacientes
            if self.request.method in SAFE_METHODS
            else EsAdminClinicaORecepcionista
        )
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            permiso_rol(),
        ]

    def get_queryset(self):
        queryset = queryset_tenant(Paciente, self.request)
        queryset = pacientes_accesibles_para_usuario(queryset, self.request.user)
        queryset = queryset.select_related(
            "usuario"
        ).prefetch_related("usuario__roles_asignados__rol")

        estado = self.request.query_params.get("estado")
        if estado is not None:
            valores = {
                "true": True,
                "1": True,
                "si": True,
                "false": False,
                "0": False,
                "no": False,
            }
            if estado.lower() not in valores:
                raise ValidationError({"estado": ["Use true o false."]})
            queryset = queryset.filter(estado=valores[estado.lower()])

        sexo = self.request.query_params.get("sexo")
        if sexo:
            sexo = sexo.upper()
            if sexo not in Sexo.values:
                raise ValidationError(
                    {"sexo": ["Valor de sexo inválido."]}
                )
            queryset = queryset.filter(sexo=sexo)

        return queryset

    @extend_schema(
        tags=["Pacientes"],
        parameters=[ConsultaIdentidadSerializer],
        responses={200: IdentidadCompartidaSerializer},
        description=(
            "Busca en Personal la identidad de la misma clínica con CI exacta."
        ),
    )
    @action(detail=False, methods=["get"], url_path="identidad-por-ci")
    def identidad_por_ci(self, request):
        parametros = ConsultaIdentidadSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        personal = (
            Personal.all_objects.select_related("usuario")
            .filter(
                clinica=request.user.clinica,
                ci=parametros.validated_data["ci"],
            )
            .first()
        )
        return Response(respuesta_identidad(personal, "PERSONAL"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paciente = crear_paciente(
            request.user.clinica,
            dict(serializer.validated_data),
        )
        return Response(
            self.get_serializer(paciente).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        paciente = self.get_object()
        serializer = self.get_serializer(
            paciente,
            data=request.data,
            partial=kwargs.pop("partial", False),
        )
        serializer.is_valid(raise_exception=True)
        paciente = actualizar_paciente(
            paciente,
            dict(serializer.validated_data),
        )
        return Response(self.get_serializer(paciente).data)

    def destroy(self, request, *args, **kwargs):
        desactivar_paciente(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Pacientes"],
        description=(
            "Vincula un paciente activo con una cuenta activa de la misma clínica "
            "que tenga el rol Paciente. Es idempotente para la misma relación y no "
            "permite reemplazar ni desvincular cuentas."
        ),
        request=VincularUsuarioPacienteSerializer,
        responses={
            200: VincularUsuarioPacienteRespuestaSerializer,
            400: OpenApiResponse(description="Usuario no válido (usuario_no_valido)."),
            403: OpenApiResponse(description="Sin permiso o suscripción vigente."),
            404: OpenApiResponse(description="Paciente o usuario no encontrado."),
            409: OpenApiResponse(description="Paciente o usuario ya vinculado, o paciente inactivo."),
        },
    )
    @action(detail=True, methods=["post"], url_path="vincular-usuario")
    def vincular_usuario(self, request, pk=None):
        entrada = VincularUsuarioPacienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        paciente = vincular_usuario_paciente(
            clinica=request.user.clinica,
            paciente_id=pk,
            usuario_id=entrada.validated_data["usuario_id"],
        )
        return Response({
            "codigo": "usuario_vinculado",
            "mensaje": "Usuario vinculado correctamente.",
            "paciente_id": paciente.pk,
            "usuario_id": paciente.usuario_id,
        })

    @extend_schema(
        tags=["Pacientes"],
        request=CrearCuentaPacienteSerializer,
        responses={201: PacienteSerializer, **ERRORES},
        description="Crea una cuenta con rol Paciente y la vincula atómicamente.",
    )
    @action(detail=True, methods=["post"], url_path="crear-cuenta")
    def crear_cuenta(self, request, pk=None):
        entrada = CrearCuentaPacienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        paciente = crear_cuenta_para_paciente(
            clinica=request.user.clinica,
            paciente_id=pk,
            datos=dict(entrada.validated_data),
        )
        return Response(PacienteSerializer(paciente).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Pacientes"],
        parameters=[BuscarCuentasElegiblesSerializer],
        responses={200: UsuarioSerializer(many=True), **ERRORES},
        description="Lista cuentas verificables por Personal con la misma CI.",
    )
    @action(detail=True, methods=["get"], url_path="cuentas-elegibles")
    def cuentas_elegibles(self, request, pk=None):
        parametros = BuscarCuentasElegiblesSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        paciente = Paciente.all_objects.filter(
            pk=pk, clinica=request.user.clinica
        ).first()
        if paciente is None:
            from apps.core.api_exceptions import RecursoNoEncontrado

            raise RecursoNoEncontrado("Paciente no encontrado.")
        queryset = cuentas_elegibles_para_paciente(
            clinica=request.user.clinica,
            paciente=paciente,
            search=parametros.validated_data.get("search", "").strip(),
        )
        pagina = self.paginate_queryset(queryset)
        serializer = UsuarioSerializer(pagina, many=True)
        return self.get_paginated_response(serializer.data)


ERRORES_ENFERMEDAD = {
    400: OpenApiResponse(
        description=(
            "Datos inválidos, incluido fecha_deteccion_invalida."
        )
    ),
    401: OpenApiResponse(description="No autenticado."),
    403: OpenApiResponse(
        description=(
            "Rol no permitido, clínica inactiva o suscripción vencida."
        )
    ),
    404: OpenApiResponse(
        description=(
            "Paciente o enfermedad inexistente, ajena a la clínica o que "
            "no corresponde con la ruta (no_encontrado)."
        )
    ),
    409: OpenApiResponse(
        description=(
            "El paciente existe, pero no tiene historia clínica "
            "(historia_no_disponible)."
        )
    ),
}


@extend_schema_view(
    list=extend_schema(
        tags=["Enfermedades"],
        description=(
            "Lista las enfermedades de la historia del paciente. Permitido "
            "para médicos y administradores de clínica."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter("tipo", str, enum=TipoEnfermedad.values),
            OpenApiParameter("severidad", str, enum=Severidad.values),
            OpenApiParameter(
                "ordering",
                str,
                description=(
                    "Ordena por fecha_deteccion o nombre; use - para orden "
                    "descendente. El valor predeterminado es "
                    "-fecha_deteccion."
                ),
            ),
        ],
        responses={200: EnfermedadSerializer(many=True), **ERRORES_ENFERMEDAD},
    ),
    create=extend_schema(
        tags=["Enfermedades"],
        description=(
            "Registra una enfermedad en la historia del paciente. Solo los "
            "médicos pueden realizar esta operación; la historia se resuelve "
            "en el backend y no se acepta desde el cuerpo."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            )
        ],
        request=EnfermedadSerializer,
        responses={201: EnfermedadSerializer, **ERRORES_ENFERMEDAD},
    ),
    retrieve=extend_schema(
        tags=["Enfermedades"],
        description=(
            "Consulta una enfermedad de la historia del paciente. Permitido "
            "para médicos y administradores de clínica."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                "enfermedad_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
        ],
        responses={200: EnfermedadSerializer, **ERRORES_ENFERMEDAD},
    ),
    partial_update=extend_schema(
        tags=["Enfermedades"],
        description=(
            "Actualiza parcialmente una enfermedad sin cambiar su historia. "
            "Solo los médicos pueden realizar esta operación."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                "enfermedad_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
        ],
        request=EnfermedadSerializer,
        responses={200: EnfermedadSerializer, **ERRORES_ENFERMEDAD},
    ),
)
class EnfermedadViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Antecedentes de enfermedad anidados bajo un paciente tenant-safe."""

    serializer_class = EnfermedadSerializer
    queryset = Enfermedad.all_objects.none()
    lookup_url_kwarg = "enfermedad_id"
    http_method_names = ["get", "post", "patch", "head", "options"]
    ordering_fields = ("fecha_deteccion", "nombre")
    ordering = ("-fecha_deteccion",)

    def get_permissions(self):
        permiso_rol = (
            PuedeConsultarEnfermedades
            if self.request.method in SAFE_METHODS
            else EsMedico
        )
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            permiso_rol(),
        ]

    def _paciente(self):
        if not hasattr(self, "_paciente_cache"):
            self._paciente_cache = get_object_or_404(
                pacientes_accesibles_para_usuario(
                    queryset_tenant(Paciente, self.request), self.request.user
                ),
                pk=self.kwargs["paciente_id"],
            )
        return self._paciente_cache

    def _historia(self):
        if not hasattr(self, "_historia_cache"):
            self._historia_cache = obtener_historia_paciente(
                self._paciente()
            )
        return self._historia_cache

    def get_queryset(self):
        usuario = getattr(self.request, "user", None)
        if not getattr(usuario, "is_authenticated", False):
            return Enfermedad.all_objects.none()

        queryset = queryset_tenant(Enfermedad, self.request).filter(
            historia=self._historia()
        )
        tipo = self.request.query_params.get("tipo")
        if tipo:
            tipo = tipo.upper()
            if tipo not in TipoEnfermedad.values:
                raise ValidationError({"tipo": ["Tipo inválido."]})
            queryset = queryset.filter(tipo=tipo)

        severidad = self.request.query_params.get("severidad")
        if severidad:
            severidad = severidad.upper()
            if severidad not in Severidad.values:
                raise ValidationError(
                    {"severidad": ["Severidad inválida."]}
                )
            queryset = queryset.filter(severidad=severidad)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enfermedad = crear_enfermedad(
            self._historia(),
            dict(serializer.validated_data),
        )
        return Response(
            self.get_serializer(enfermedad).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        enfermedad = self.get_object()
        serializer = self.get_serializer(
            enfermedad,
            data=request.data,
            partial=kwargs.pop("partial", False),
        )
        serializer.is_valid(raise_exception=True)
        enfermedad = actualizar_enfermedad(
            enfermedad,
            dict(serializer.validated_data),
        )
        return Response(self.get_serializer(enfermedad).data)


ERRORES_ALERGIA = {
    400: OpenApiResponse(description="Datos inválidos."),
    401: OpenApiResponse(description="No autenticado."),
    403: OpenApiResponse(
        description=(
            "Rol no permitido, clínica inactiva o suscripción vencida."
        )
    ),
    404: OpenApiResponse(
        description=(
            "Paciente o alergia inexistente, ajena a la clínica o que no "
            "corresponde con la ruta (no_encontrado)."
        )
    ),
    409: OpenApiResponse(
        description=(
            "Paciente sin historia (historia_no_disponible) o nombre "
            "duplicado en la historia (alergia_duplicada)."
        )
    ),
}


@extend_schema_view(
    list=extend_schema(
        tags=["Alergias"],
        description=(
            "Lista las alergias de la historia del paciente. Permitido para "
            "médicos y administradores de clínica."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter("tipo", str, enum=TipoAlergia.values),
            OpenApiParameter("severidad", str, enum=Severidad.values),
            OpenApiParameter(
                "ordering",
                str,
                description=(
                    "Ordena por nombre, tipo o severidad; use - para orden "
                    "descendente. El valor predeterminado es nombre."
                ),
            ),
        ],
        responses={200: AlergiaSerializer(many=True), **ERRORES_ALERGIA},
    ),
    create=extend_schema(
        tags=["Alergias"],
        description=(
            "Registra una alergia en la historia del paciente. Solo los "
            "médicos pueden realizar esta operación. La historia se resuelve "
            "en el backend; alergia_duplicada identifica un nombre repetido."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            )
        ],
        request=AlergiaSerializer,
        responses={201: AlergiaSerializer, **ERRORES_ALERGIA},
    ),
    retrieve=extend_schema(
        tags=["Alergias"],
        description=(
            "Consulta una alergia de la historia del paciente. Permitido "
            "para médicos y administradores de clínica."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                "alergia_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
        ],
        responses={200: AlergiaSerializer, **ERRORES_ALERGIA},
    ),
    partial_update=extend_schema(
        tags=["Alergias"],
        description=(
            "Actualiza parcialmente una alergia sin cambiar su historia. "
            "Solo los médicos pueden realizar esta operación; un nombre "
            "repetido devuelve alergia_duplicada."
        ),
        parameters=[
            OpenApiParameter(
                "paciente_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                "alergia_id",
                OpenApiTypes.INT,
                OpenApiParameter.PATH,
            ),
        ],
        request=AlergiaSerializer,
        responses={200: AlergiaSerializer, **ERRORES_ALERGIA},
    ),
)
class AlergiaViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Alergias anidadas bajo el paciente y su historia tenant-safe."""

    serializer_class = AlergiaSerializer
    queryset = Alergia.all_objects.none()
    lookup_url_kwarg = "alergia_id"
    http_method_names = ["get", "post", "patch", "head", "options"]
    ordering_fields = ("nombre", "tipo", "severidad")
    ordering = ("nombre",)

    def get_permissions(self):
        permiso_rol = (
            PuedeConsultarAlergias
            if self.request.method in SAFE_METHODS
            else EsMedico
        )
        return [
            TieneClinica(),
            TieneSuscripcionVigente(),
            permiso_rol(),
        ]

    def _paciente(self):
        if not hasattr(self, "_paciente_cache"):
            self._paciente_cache = get_object_or_404(
                pacientes_accesibles_para_usuario(
                    queryset_tenant(Paciente, self.request), self.request.user
                ),
                pk=self.kwargs["paciente_id"],
            )
        return self._paciente_cache

    def _historia(self):
        if not hasattr(self, "_historia_cache"):
            self._historia_cache = obtener_historia_paciente(
                self._paciente()
            )
        return self._historia_cache

    def get_queryset(self):
        usuario = getattr(self.request, "user", None)
        if not getattr(usuario, "is_authenticated", False):
            return Alergia.all_objects.none()

        queryset = queryset_tenant(Alergia, self.request).filter(
            historia=self._historia()
        )
        tipo = self.request.query_params.get("tipo")
        if tipo:
            tipo = tipo.upper()
            if tipo not in TipoAlergia.values:
                raise ValidationError({"tipo": ["Tipo inválido."]})
            queryset = queryset.filter(tipo=tipo)

        severidad = self.request.query_params.get("severidad")
        if severidad:
            severidad = severidad.upper()
            if severidad not in Severidad.values:
                raise ValidationError(
                    {"severidad": ["Severidad inválida."]}
                )
            queryset = queryset.filter(severidad=severidad)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alergia = crear_alergia(
            self._historia(),
            dict(serializer.validated_data),
        )
        return Response(
            self.get_serializer(alergia).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        alergia = self.get_object()
        serializer = self.get_serializer(
            alergia,
            data=request.data,
            partial=kwargs.pop("partial", False),
        )
        serializer.is_valid(raise_exception=True)
        alergia = actualizar_alergia(
            alergia,
            dict(serializer.validated_data),
        )
        return Response(self.get_serializer(alergia).data)
