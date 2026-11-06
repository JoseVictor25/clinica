"""Managers y modelos abstractos para el aislamiento por clínica."""

from django.core.exceptions import ValidationError
from django.db import models

from .exceptions import ClinicaAjena
from .tenant import esta_en_bypass, get_clinica_actual


class TenantQuerySet(models.QuerySet):
    """QuerySet con utilidades para el filtrado por clínica."""

    def for_clinica(self, clinica):
        lookup = getattr(self.model, "tenant_lookup", "clinica")
        return self.filter(**{lookup: clinica})

    def sin_filtro(self):
        """Devuelve el queryset sin filtro adicional (no evita el del manager)."""
        return self


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """
    Manager que filtra automáticamente por la clínica activa.

    Si no hay contexto, falla cerrado. Para operaciones de sistema se usa
    el manager `all_objects`.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        if esta_en_bypass():
            return queryset

        clinica = get_clinica_actual()
        if clinica is None:
            # Usuario autenticado sin clínica: no ve datos tenant.
            return queryset.none()

        return queryset.for_clinica(clinica)


class TenantBaseMixin:
    """
    Comportamiento común de asignación/validación de clínica.

    `tenant_lookup` indica la ruta desde el registro hasta su clínica:
      - Modelos raíz: "clinica".
      - Modelos hijos: "paciente__clinica", "historia__paciente__clinica", etc.
    """

    tenant_lookup = "clinica"
    tenant_clinica_obligatoria = True

    def clinica_del_registro(self):
        """Recorre tenant_lookup y devuelve la clínica del registro o None."""
        if not self.tenant_lookup:
            return None
        objeto = self
        for parte in self.tenant_lookup.split("__"):
            objeto = getattr(objeto, parte, None)
            if objeto is None:
                return None
        return objeto

    def save(self, *args, **kwargs):
        contexto = get_clinica_actual(opcional=True)
        es_modelo_raiz = self.tenant_lookup == "clinica"

        if self._state.adding and es_modelo_raiz and not getattr(self, "clinica_id", None):
            if contexto is not None and not getattr(
                self, "_evitar_clinica_contexto", False
            ):
                self.clinica = contexto
            elif contexto is None and self.tenant_clinica_obligatoria:
                raise ValidationError(
                    "No se pudo determinar la clínica del registro. "
                    "La clínica debe asignarse desde el usuario autenticado."
                )

        clinica_registro = self.clinica_del_registro()
        if (
            contexto is not None
            and clinica_registro is not None
            and clinica_registro.pk != contexto.pk
        ):
            raise ClinicaAjena(
                "No está permitido guardar registros pertenecientes a otra clínica."
            )

        super().save(*args, **kwargs)


class TenantModel(TenantBaseMixin, models.Model):
    """Modelo abstracto para entidades raíz que llevan clinica_id."""

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class TenantChildModel(TenantBaseMixin, models.Model):
    """Modelo abstracto para entidades hijas que heredan la clínica del padre."""

    tenant_clinica_obligatoria = False

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
