from django.contrib import admin

from apps.core.admin import TenantAdminMixin

from .models import Alergia, Enfermedad, HistoriaClinica, Paciente


@admin.register(Paciente)
class PacienteAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "apellido",
        "nombre",
        "ci",
        "sexo",
        "clinica",
        "estado",
    )
    search_fields = ("apellido", "nombre", "ci")
    list_filter = ("sexo", "estado", "clinica")
    date_hierarchy = "fecha_nacimiento"


@admin.register(HistoriaClinica)
class HistoriaClinicaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "paciente",
        "fecha_apertura",
        "grupo_sanguineo",
        "estado",
    )
    search_fields = ("paciente__apellido", "paciente__nombre")
    list_filter = ("grupo_sanguineo", "estado")


@admin.register(Enfermedad)
class EnfermedadAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "nombre",
        "historia",
        "tipo",
        "severidad",
        "fecha_deteccion",
    )
    search_fields = ("nombre", "historia__paciente__apellido")
    list_filter = ("tipo", "severidad")
    date_hierarchy = "fecha_deteccion"


@admin.register(Alergia)
class AlergiaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "historia", "tipo", "severidad")
    search_fields = ("nombre", "historia__paciente__apellido")
    list_filter = ("tipo", "severidad")
