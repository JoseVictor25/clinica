"""Configuración específica para la ejecución de pruebas."""

from .settings import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Las pruebas renderizan el admin sin ejecutar collectstatic. El manifiesto
# comprimido de WhiteNoise se reserva para el arranque de produccion.
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Hash rápido solo para pruebas; nunca se usa en desarrollo ni producción.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
