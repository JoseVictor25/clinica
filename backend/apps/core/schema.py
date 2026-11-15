"""Esquema de seguridad OpenAPI para la autenticación JWT multitenant."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TenantJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Declara el botón Authorize como Bearer JWT en Swagger UI."""

    target_class = "apps.core.authentication.TenantJWTAuthentication"
    name = "Bearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Token JWT obtenido en /api/v1/auth/login/. "
                "Enviar como: Authorization: Bearer <access>."
            ),
        }
