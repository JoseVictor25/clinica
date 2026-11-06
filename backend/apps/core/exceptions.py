"""Excepciones propias del aislamiento multitenant."""


class TenantError(Exception):
    """Error base de la capa multitenant."""


class TenantNoConfigurado(TenantError):
    """No se ha fijado una clínica activa para la petición o el proceso."""


class ClinicaRequerida(TenantError):
    """La operación requiere una clínica, pero el usuario no tiene una."""


class ClinicaAjena(TenantError):
    """Se intentó crear o modificar un registro de otra clínica."""
