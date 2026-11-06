"""Autenticación JWT que fija la clínica activa después de validar el token."""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings

from .tenant import set_bypass, set_clinica_actual


class TenantJWTAuthentication(JWTAuthentication):
    """
    Extiende JWTAuthentication para resolver la clínica del usuario.

    No se confía en un claim de clínica del token: se consulta la BD para evitar
    tokens obsoletos si el usuario cambia de clínica o es desactivado.
    """

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as exc:
            raise AuthenticationFailed(
                "Token inválido: no contiene el identificador de usuario."
            ) from exc

        # Import local para evitar problemas de registro de apps al cargar settings.
        from apps.seguridad.models import Usuario

        try:
            usuario = Usuario.all_objects.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except Usuario.DoesNotExist as exc:
            raise AuthenticationFailed("Usuario no encontrado.") from exc

        if not usuario.is_active:
            raise AuthenticationFailed("El usuario está inactivo.")

        if usuario.clinica_id:
            set_clinica_actual(usuario.clinica)
        elif usuario.is_superuser:
            set_bypass()
        else:
            raise AuthenticationFailed(
                "El usuario no está asociado a una clínica."
            )

        return usuario
