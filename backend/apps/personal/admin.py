from django.contrib import admin

from apps.core.admin import TenantAdminMixin

from .models import Especialidad, HorarioAtencion, Medico, Personal


@admin.register(Personal)
class PersonalAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("apellido", "nombre", "ci", "cargo", "clinica", "estado")
    search_fields = ("apellido", "nombre", "ci")
    list_filter = ("cargo", "estado", "clinica")


@admin.register(Especialidad)
class EspecialidadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "clinica", "estado")
    search_fields = ("nombre",)
    list_filter = ("estado", "clinica")


@admin.register(Medico)
class MedicoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "personal",
        "numero_colegiatura",
        "especialidad",
        "clinica",
        "estado",
    )
    search_fields = (
        "personal__apellido",
        "personal__nombre",
        "numero_colegiatura",
    )
    list_filter = ("estado", "especialidad", "clinica")


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("medico", "dia_semana", "hora_inicio", "hora_fin")
    search_fields = (
        "medico__personal__apellido",
        "medico__personal__nombre",
    )
    list_filter = ("dia_semana",)
