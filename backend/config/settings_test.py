"""Configuración específica para la ejecución de pruebas."""

from .settings import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Hash rápido solo para pruebas; nunca se usa en desarrollo ni producción.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
