"""Utilidades de administración para modelos tenant."""

from django.contrib import admin


class TenantAdminMixin:
    """
    En el admin de plataforma se usa all_objects para que el superusuario
    pueda inspeccionar todos los tenants. Los endpoints de negocio NO usan
    este mixin y siguen el filtrado estricto.
    """

    def get_queryset(self, request):
        return self.model.all_objects.all()
