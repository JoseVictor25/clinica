from django.contrib import admin

from apps.core.admin import TenantAdminMixin

from .models import Clinica, PlanSuscripcion, Suscripcion


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "telefono", "email", "estado")
    search_fields = ("nombre", "nit")
    list_filter = ("estado",)


@admin.register(PlanSuscripcion)
class PlanSuscripcionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "max_usuarios", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)


@admin.register(Suscripcion)
class SuscripcionAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("clinica", "plan", "fecha_inicio", "fecha_fin", "estado")
    search_fields = ("clinica__nombre", "plan__nombre")
    list_filter = ("estado", "plan")
    date_hierarchy = "fecha_inicio"
