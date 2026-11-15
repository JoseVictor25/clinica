"""Excepciones de API y formato uniforme de errores."""

from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler


class ErrorNegocio(APIException):
    """Error de negocio con código estable para el cliente."""

    status_code = 400
    default_detail = "No se pudo completar la operación."
    codigo = "regla_negocio"

    def __init__(self, mensaje=None, codigo=None, detalles=None):
        self.codigo = codigo or self.codigo
        self.detalles = detalles
        super().__init__(detail=mensaje or self.default_detail)


class DatosInvalidos(ErrorNegocio):
    status_code = 400
    codigo = "datos_invalidos"


class CredencialesInvalidas(ErrorNegocio):
    status_code = 401
    codigo = "credenciales_invalidas"


class PermisoDenegado(ErrorNegocio):
    status_code = 403
    codigo = "permiso_denegado"


class SuscripcionVencida(ErrorNegocio):
    status_code = 403
    codigo = "suscripcion_vencida"


class ClinicaInactiva(ErrorNegocio):
    status_code = 403
    codigo = "clinica_inactiva"


class RecursoNoEncontrado(ErrorNegocio):
    status_code = 404
    codigo = "no_encontrado"


class Conflicto(ErrorNegocio):
    status_code = 409
    codigo = "conflicto"


class LimiteUsuarios(ErrorNegocio):
    status_code = 409
    codigo = "limite_usuarios"


def _detalle_texto(detalle):
    if isinstance(detalle, str):
        return detalle
    if isinstance(detalle, (list, tuple)) and detalle:
        return _detalle_texto(detalle[0])
    if isinstance(detalle, dict):
        for valor in detalle.values():
            return _detalle_texto(valor)
    return "No se pudo completar la operación."


def manejador_excepciones(exc, context):
    """Normaliza todas las respuestas de error de DRF."""
    response = exception_handler(exc, context)

    # Errores no gestionados por DRF se dejan a Django.
    if response is None:
        return None

    if isinstance(exc, ErrorNegocio):
        body = {
            "codigo": exc.codigo,
            "mensaje": _detalle_texto(exc.detail),
        }
        if exc.detalles:
            body["detalles"] = exc.detalles
        response.data = body
        return response

    if isinstance(exc, ValidationError):
        response.data = {
            "codigo": "datos_invalidos",
            "mensaje": "Datos inválidos.",
            "detalles": response.data,
        }
        return response

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        response.data = {
            "codigo": "no_autenticado",
            "mensaje": _detalle_texto(response.data),
        }
        return response

    if isinstance(exc, PermissionDenied):
        response.data = {
            "codigo": "permiso_denegado",
            "mensaje": _detalle_texto(response.data),
        }
        return response

    if isinstance(exc, (NotFound, Http404)):
        response.data = {
            "codigo": "no_encontrado",
            "mensaje": "El recurso no existe o no pertenece a su clínica.",
        }
        return response

    if isinstance(exc, Throttled):
        response.data = {
            "codigo": "demasiados_intentos",
            "mensaje": "Demasiados intentos. Intente nuevamente más tarde.",
        }
        return response

    # Errores de SimpleJWT y otros APIException.
    codigo = getattr(exc, "default_code", "error")
    response.data = {
        "codigo": codigo,
        "mensaje": _detalle_texto(response.data),
    }
    return response
