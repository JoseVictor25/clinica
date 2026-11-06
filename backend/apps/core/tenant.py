"""
Contexto de la clínica activa.

Se usa contextvars (no threading.local) para que el aislamiento funcione también
con código asíncrono. El contexto se fija por petición en TenantMiddleware para
sesiones y en TenantJWTAuthentication para JWT.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from .exceptions import TenantNoConfigurado


class _SinDefinir:
    def __repr__(self):  # pragma: no cover - ayuda de depuración
        return "<sin-definir>"


SIN_DEFINIR = _SinDefinir()

_clinica_actual: ContextVar = ContextVar("clinica_actual", default=SIN_DEFINIR)
_bypass: ContextVar[bool] = ContextVar("tenant_bypass", default=False)


def set_clinica_actual(clinica):
    """Fija la clínica activa y desactiva el modo bypass."""
    _clinica_actual.set(clinica)
    _bypass.set(False)


def set_bypass():
    """
    Activa el modo sin filtro para el administrador del sistema.

    Solo debe usarse en el admin de plataforma, comandos de gestión y pruebas
    explícitas. Los endpoints tenant rechazan al usuario sin clínica.
    """
    _clinica_actual.set(None)
    _bypass.set(True)


def get_clinica_actual(opcional=False):
    """
    Devuelve la clínica activa.

    - Si nunca se configuró, lanza TenantNoConfigurado (falla cerrado).
    - Si se configuró explícitamente como None, devuelve None (usuario sin clínica).
    - Con opcional=True, devuelve None cuando no hay contexto en lugar de lanzar.
    """
    valor = _clinica_actual.get()
    if valor is SIN_DEFINIR:
        if opcional:
            return None
        raise TenantNoConfigurado(
            "No hay una clínica activa en el contexto. "
            "Use tenant_context(), la autenticación JWT o all_objects para operaciones de sistema."
        )
    return valor


def esta_en_bypass():
    return bool(_bypass.get())


def limpiar_contexto():
    """Restablece el contexto al estado inicial."""
    _clinica_actual.set(SIN_DEFINIR)
    _bypass.set(False)


@contextmanager
def contexto_limpio():
    """
    Aísla el contexto de una petición y lo restaura al terminar.

    Se usan tokens de ContextVar para que, incluso si el contexto previo tenía
    una clínica o bypass (por ejemplo, una prueba que envuelve una petición),
    el estado se restaure correctamente al salir y no se filtre a la siguiente
    petición del mismo hilo o tarea.
    """
    token_clinica = _clinica_actual.set(SIN_DEFINIR)
    token_bypass = _bypass.set(False)
    try:
        yield
    finally:
        _clinica_actual.reset(token_clinica)
        _bypass.reset(token_bypass)


@contextmanager
def tenant_context(clinica=None, bypass=False):
    """
    Context manager para fijar la clínica activa en pruebas, comandos o servicios.

    Ejemplos:
        with tenant_context(clinica_a):
            Paciente.objects.all()

        with tenant_context(bypass=True):
            Clinica.objects.all()
    """
    token_clinica = _clinica_actual.set(None if bypass else clinica)
    token_bypass = _bypass.set(bool(bypass))
    try:
        yield
    finally:
        _clinica_actual.reset(token_clinica)
        _bypass.reset(token_bypass)
