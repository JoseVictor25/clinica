"""Utilidades para querysets tenant seguros durante la generación de esquema."""

from apps.core.fields import TenantRelatedField  # noqa: F401  (reexport)


def queryset_tenant(modelo, request):
    """
    Devuelve el queryset tenant para una petición autenticada.

    Durante la generación de OpenAPI la petición es anónima: devolver un
    queryset vacío evita que TenantManager lance TenantNoConfigurado.
    """
    usuario = getattr(request, "user", None)
    if not getattr(usuario, "is_authenticated", False):
        return modelo.all_objects.none()

    manager = getattr(modelo, "tenant_objects", None)
    if manager is None:
        manager = modelo.objects
    return manager.all()
