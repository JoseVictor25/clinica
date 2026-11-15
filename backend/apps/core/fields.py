"""Campos de relaciones que respetan el aislamiento por clínica."""

from rest_framework import serializers


class TenantRelatedField(serializers.PrimaryKeyRelatedField):
    """
    PrimaryKeyRelatedField con queryset resuelto por petición.

    No se puede usar `Model.objects.all()` a nivel de clase porque el manager
    tenant falla cerrado al importar el serializer. Con este campo el queryset
    se calcula cuando ya existe contexto de clínica.
    """

    def __init__(self, modelo, **kwargs):
        self.modelo = modelo
        kwargs.setdefault("queryset", modelo.all_objects.none())
        super().__init__(**kwargs)

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not getattr(
            request.user, "is_authenticated", False
        ):
            return self.modelo.all_objects.none()

        manager = getattr(self.modelo, "tenant_objects", None)
        if manager is None:
            manager = self.modelo.objects
        return manager.all()
