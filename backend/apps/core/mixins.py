"""Mixins para viewsets del Sprint 1."""

from rest_framework.exceptions import PermissionDenied


class TenantViewSetMixin:
    """
    Base para viewsets tenant.

    - El queryset ya llega filtrado por TenantManager.
    - En creación, la clínica se toma del usuario autenticado, nunca del body.
    - En modelos hijos, poner tenant_asignar_clinica = False y validar el padre.
    """

    tenant_asignar_clinica = True

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        if not self.tenant_asignar_clinica:
            serializer.save()
            return

        usuario = self.request.user
        if not getattr(usuario, "clinica_id", None):
            raise PermissionDenied(
                "El usuario no está asociado a una clínica."
            )
        serializer.save(clinica=usuario.clinica)

    def perform_update(self, serializer):
        # Nunca se permite cambiar la clínica desde el body/serializer.
        serializer.save()
