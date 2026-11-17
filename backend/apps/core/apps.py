from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Núcleo"

    def ready(self):
        # Registra el esquema Bearer JWT en drf-spectacular.
        from . import schema  # noqa: F401
