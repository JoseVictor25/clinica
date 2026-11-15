"""Serializers de autenticación, usuarios y roles."""

from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api_exceptions import ClinicaInactiva
from apps.core.fields import TenantRelatedField
from apps.core.seed_data import ROLES_BASE_NOMBRES

from .models import Rol, Usuario, UsuarioRol
from .services import roles_activos


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )


class RefreshTokenSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            token = RefreshToken(attrs["refresh"])
        except TokenError as exc:
            raise serializers.ValidationError(
                {"refresh": ["Refresh token inválido o expirado."]}
            ) from exc

        user_id = token.get(api_settings.USER_ID_CLAIM)
        usuario = (
            Usuario.all_objects.select_related("clinica")
            .filter(pk=user_id)
            .first()
        )
        if usuario is None or not usuario.is_active:
            raise serializers.ValidationError(
                {"refresh": ["El usuario ya no está activo."]}
            )
        if usuario.clinica_id and not usuario.clinica.estado:
            raise ClinicaInactiva("La clínica está inactiva.")
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    password_nueva = serializers.CharField(
        write_only=True, trim_whitespace=False
    )


class UsuarioSerializer(serializers.ModelSerializer):
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "email",
            "clinica",
            "clinica_nombre",
            "estado",
            "is_staff",
            "is_superuser",
            "fecha_creacion",
            "roles",
        )
        read_only_fields = fields

    def get_roles(self, obj) -> list[str]:
        return roles_activos(obj)


class UsuarioCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    estado = serializers.BooleanField(default=True)
    roles = TenantRelatedField(Rol, many=True, required=False)


class UsuarioUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    estado = serializers.BooleanField(required=False)
    password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False
    )


class RolSerializer(serializers.ModelSerializer):
    es_base = serializers.SerializerMethodField()
    clinica_nombre = serializers.CharField(
        source="clinica.nombre", read_only=True
    )

    class Meta:
        model = Rol
        fields = (
            "id",
            "clinica",
            "clinica_nombre",
            "nombre",
            "descripcion",
            "estado",
            "es_base",
        )
        read_only_fields = ("id", "clinica", "clinica_nombre", "es_base")

    def get_es_base(self, obj) -> bool:
        return obj.nombre in ROLES_BASE_NOMBRES


class UsuarioRolSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(
        source="usuario.username", read_only=True
    )
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)
    usuario = TenantRelatedField(Usuario)
    rol = TenantRelatedField(Rol)

    class Meta:
        model = UsuarioRol
        fields = (
            "id",
            "usuario",
            "usuario_username",
            "rol",
            "rol_nombre",
            "fecha_asignacion",
        )
        read_only_fields = (
            "id",
            "usuario_username",
            "rol_nombre",
            "fecha_asignacion",
        )
        # La duplicidad se valida en el servicio (rol_ya_asignado -> 409).
        validators = []


class PerfilSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    clinica = serializers.IntegerField(allow_null=True)
    clinica_nombre = serializers.CharField(allow_null=True)
    roles = serializers.ListField(child=serializers.CharField())
    estado = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    suscripcion_vigente = serializers.BooleanField()
    suscripcion_fin = serializers.DateField(allow_null=True)
    acceso_restringido = serializers.BooleanField()


class CambiarPasswordRespuestaSerializer(serializers.Serializer):
    mensaje = serializers.CharField()
    codigo = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    mensaje = serializers.CharField()
    detalles = serializers.JSONField(required=False)
