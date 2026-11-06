"""Middleware que limpia y fija el contexto de clínica para sesiones."""

from .tenant import contexto_limpio, set_bypass, set_clinica_actual


class TenantMiddleware:
    """
    Debe colocarse después de AuthenticationMiddleware.

    - Para autenticación por sesión (admin de Django), fija la clínica del usuario.
    - Para JWT, request.user aún es anónimo aquí; la clínica la fija
      TenantJWTAuthentication dentro de DRF.
    - Aísla el contexto por petición con tokens de ContextVar y lo restaura en
      el finally, incluso si la vista lanza una excepción.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with contexto_limpio():
            usuario = getattr(request, "user", None)
            if usuario is not None and usuario.is_authenticated:
                self._configurar_contexto(usuario)
            return self.get_response(request)

    @staticmethod
    def _configurar_contexto(usuario):
        if getattr(usuario, "clinica_id", None):
            set_clinica_actual(usuario.clinica)
        elif getattr(usuario, "is_superuser", False):
            set_bypass()
