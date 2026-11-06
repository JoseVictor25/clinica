"""Vistas de autenticación, usuarios y roles."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    EsAdminClinica,
    TieneClinica,
    TieneSuscripcionVigente,
)
from apps.core.querysets import queryset_tenant
from apps.core.throttles import LoginThrottle

from .models import Rol, Usuario, UsuarioRol
from .serializers import (
    CambiarPasswordRespuestaSerializer,
    CambiarPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PerfilSerializer,
    RefreshTokenSerializer,
    RolSerializer,
    UsuarioCreateSerializer,
    UsuarioRolSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
)
from .services import (
    actualizar_rol,
    actualizar_usuario_clinica,
    asignar_rol,
    autenticar_usuario,
    cambiar_password,
    cerrar_sesion,
    crear_rol,
    crear_usuario_clinica,
    desactivar_usuario,
    emitir_tokens,
    eliminar_rol,
    perfil_usuario,
    quitar_rol,
)

ERRORES_COMUNES = {
    400: OpenApiResponse(description="Datos inválidos (datos_invalidos)."),
    401: OpenApiResponse(description="No autenticado (no_autenticado)."),
    403: OpenApiResponse(
        description=(
            "Sin permiso (permiso_denegado), suscripción vencida "
            "(suscripcion_vencida) o clínica inactiva (clinica_inactiva)."
        )
    ),
    404: OpenApiResponse(
        description="No encontrado o de otra clínica (no_encontrado)."
    ),
    409: OpenApiResponse(
        description=(
            "Conflicto de negocio: usuario_duplicado, email_duplicado, "
            "limite_usuarios, ultimo_administrador, rol_duplicado, "
            "rol_base_protegido, rol_con_asignaciones, rol_ya_asignado."
        )
    ),
}


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Tokens y perfil del usuario."),
            401: OpenApiResponse(description="Credenciales inválidas (credenciales_invalidas)."),
            403: OpenApiResponse(description="Suscripción vencida (suscripcion_vencida) o clínica inactiva."),
            429: OpenApiResponse(description="Demasiados intentos (demasiados_intentos)."),
        },
        auth=[],
        description="Inicia sesión. El administrador de clínica sin suscripción entra en modo restringido.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario, restringido = autenticar_usuario(
            serializer.validated_data["username"],
            serializer.validated_data["password"],
        )
        tokens = emitir_tokens(usuario, restringido)
        return Response(
            {
                **tokens,
                "acceso_restringido": restringido,
                "usuario": PerfilSerializer(perfil_usuario(usuario)).data,
            }
        )


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(description="Nuevo access token."),
            400: OpenApiResponse(description="Refresh inválido (datos_invalidos)."),
            403: OpenApiResponse(
                description="Clínica inactiva (clinica_inactiva)."
            ),
        },
        auth=[],
        description="Renueva el access token y rota el refresh.",
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={
            204: OpenApiResponse(description="Sesión cerrada."),
            400: OpenApiResponse(description="Refresh inválido (refresh_invalido)."),
        },
        description="Invalida el refresh token en la blacklist.",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cerrar_sesion(serializer.validated_data["refresh"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PerfilSerializer},
        description="Perfil del usuario autenticado, sus roles y su suscripción.",
    )
    def get(self, request):
        return Response(
            PerfilSerializer(perfil_usuario(request.user)).data
        )


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CambiarPasswordSerializer,
        responses={
            200: CambiarPasswordRespuestaSerializer,
            400: OpenApiResponse(
                description="Contraseña actual incorrecta o nueva inválida (datos_invalidos)."
            ),
        },
        description="Cambia la contraseña del usuario autenticado.",
    )
    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cambiar_password(
            request.user,
            serializer.validated_data["password_actual"],
            serializer.validated_data["password_nueva"],
        )
        return Response(
            {
                "codigo": "password_actualizada",
                "mensaje": "Contraseña actualizada correctamente.",
            }
        )


class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [
        TieneClinica,
        TieneSuscripcionVigente,
        EsAdminClinica,
    ]
    search_fields = ("username", "email")
    ordering_fields = ("username", "email", "fecha_creacion", "estado")
    ordering = ("username",)

    def get_queryset(self):
        return queryset_tenant(Usuario, self.request)

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action in ("update", "partial_update"):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    @extend_schema(
        request=UsuarioCreateSerializer,
        responses={201: UsuarioSerializer, **ERRORES_COMUNES},
        description="Crea un usuario de la clínica. El password nunca se devuelve.",
    )
    def create(self, request, *args, **kwargs):
        serializer = UsuarioCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        datos = dict(serializer.validated_data)
        roles = datos.pop("roles", [])
        usuario = crear_usuario_clinica(
            request.user.clinica, datos, roles=roles
        )
        return Response(
            UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        usuario = self.get_object()
        serializer = UsuarioUpdateSerializer(
            data=request.data,
            partial=parcial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        actualizar_usuario_clinica(
            usuario, dict(serializer.validated_data)
        )
        return Response(UsuarioSerializer(usuario).data)

    def destroy(self, request, *args, **kwargs):
        desactivar_usuario(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolViewSet(viewsets.ModelViewSet):
    serializer_class = RolSerializer
    permission_classes = [
        TieneClinica,
        TieneSuscripcionVigente,
        EsAdminClinica,
    ]
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "estado")
    ordering = ("nombre",)

    def get_queryset(self):
        qs = queryset_tenant(Rol, self.request)
        estado = self.request.query_params.get("estado")
        if estado is not None:
            qs = qs.filter(estado=estado.lower() in ("1", "true", "si"))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = RolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rol = crear_rol(request.user.clinica, dict(serializer.validated_data))
        return Response(
            RolSerializer(rol).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        rol = self.get_object()
        serializer = RolSerializer(
            rol, data=request.data, partial=parcial
        )
        serializer.is_valid(raise_exception=True)
        rol = actualizar_rol(rol, dict(serializer.validated_data))
        return Response(RolSerializer(rol).data)

    def destroy(self, request, *args, **kwargs):
        eliminar_rol(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioRolViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioRolSerializer
    permission_classes = [
        TieneClinica,
        TieneSuscripcionVigente,
        EsAdminClinica,
    ]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return queryset_tenant(UsuarioRol, self.request)

    def create(self, request, *args, **kwargs):
        serializer = UsuarioRolSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        asignacion = asignar_rol(
            serializer.validated_data["usuario"],
            serializer.validated_data["rol"],
        )
        return Response(
            UsuarioRolSerializer(asignacion).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        quitar_rol(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
