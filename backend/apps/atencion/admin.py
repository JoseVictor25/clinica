from django.contrib import admin

from apps.core.admin import TenantAdminMixin

from .models import Cita, Consulta, MedicamentoRecetado, Receta


@admin.register(Cita)
class CitaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "fecha",
        "hora",
        "paciente",
        "medico",
        "estado",
        "clinica",
    )
    search_fields = (
        "paciente__apellido",
        "paciente__nombre",
        "medico__personal__apellido",
    )
    list_filter = ("estado", "clinica")
    date_hierarchy = "fecha"


@admin.register(Consulta)
class ConsultaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("fecha", "paciente", "medico", "clinica")
    search_fields = (
        "paciente__apellido",
        "paciente__nombre",
        "medico__personal__apellido",
        "diagnostico",
    )
    list_filter = ("clinica",)
    date_hierarchy = "fecha"


@admin.register(Receta)
class RecetaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("fecha", "consulta")
    search_fields = ("consulta__paciente__apellido", "indicaciones")
    date_hierarchy = "fecha"


@admin.register(MedicamentoRecetado)
class MedicamentoRecetadoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "nombre_medicamento",
        "dosis",
        "frecuencia",
        "duracion",
        "receta",
    )
    search_fields = ("nombre_medicamento", "receta__consulta__paciente__apellido")
