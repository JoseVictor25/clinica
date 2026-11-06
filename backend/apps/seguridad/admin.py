from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.admin import TenantAdminMixin

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import Rol, Usuario, UsuarioRol


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = (
        "username",
        "email",
        "clinica",
        "estado",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("estado", "is_staff", "is_superuser", "clinica")
    search_fields = ("username", "email")
    ordering = ("username",)
    readonly_fields = ("last_login", "fecha_creacion")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos de la cuenta", {"fields": ("email", "clinica")}),
        (
            "Permisos",
            {
                "fields": (
                    "estado",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "fecha_creacion")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "clinica",
                    "estado",
                    "is_staff",
                    "is_superuser",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return Usuario.all_objects.all()


@admin.register(Rol)
class RolAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "clinica", "estado")
    search_fields = ("nombre", "clinica__nombre")
    list_filter = ("estado", "clinica")


@admin.register(UsuarioRol)
class UsuarioRolAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("usuario", "rol", "fecha_asignacion")
    search_fields = ("usuario__username", "rol__nombre")
    list_filter = ("rol",)
    date_hierarchy = "fecha_asignacion"
