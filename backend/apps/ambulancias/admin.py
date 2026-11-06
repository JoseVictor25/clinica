from django.contrib import admin

from apps.core.admin import TenantAdminMixin

from .models import (
    Ambulancia,
    Equipamiento,
    LicenciaConducir,
    Traslado,
)


@admin.register(Ambulancia)
class AmbulanciaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "matricula",
        "tipo",
        "estado",
        "capacidad",
        "clinica",
    )
    search_fields = ("matricula",)
    list_filter = ("tipo", "estado", "clinica")


@admin.register(Equipamiento)
class EquipamientoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "ambulancia")
    search_fields = ("nombre", "ambulancia__matricula")


@admin.register(LicenciaConducir)
class LicenciaConducirAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "numero",
        "personal",
        "categoria",
        "fecha_emision",
        "fecha_vencimiento",
    )
    search_fields = ("numero", "personal__apellido", "personal__nombre")
    list_filter = ("categoria",)
    date_hierarchy = "fecha_vencimiento"


@admin.register(Traslado)
class TrasladoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "fecha_salida",
        "paciente",
        "ambulancia",
        "conductor",
        "estado",
        "clinica",
    )
    search_fields = (
        "paciente__apellido",
        "paciente__nombre",
        "ambulancia__matricula",
        "conductor__apellido",
    )
    list_filter = ("estado", "tipo_traslado", "clinica")
    date_hierarchy = "fecha_salida"
