"""
Configuración de Django para el SaaS multitenant de clínicas.

Todos los secretos y valores sensibles se leen exclusivamente desde backend/.env
mediante python-decouple. SECRET_KEY y las credenciales de PostgreSQL no tienen
valor por defecto: si faltan, la aplicación falla con un mensaje claro.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, UndefinedValueError, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_requerido(nombre, cast=str):
    """Lee una variable obligatoria del .env y falla con un mensaje en español."""
    try:
        valor = config(nombre, cast=cast)
    except (UndefinedValueError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"Falta la variable de entorno obligatoria '{nombre}' o su valor es inválido. "
            "Revisa el archivo backend/.env (puedes tomarlo de backend/.env.example)."
        ) from exc
    if valor in (None, ""):
        raise ImproperlyConfigured(
            f"La variable de entorno obligatoria '{nombre}' está vacía. "
            "Revisa el archivo backend/.env."
        )
    return valor


# --- Seguridad básica -------------------------------------------------------
SECRET_KEY = env_requerido("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    # Apps del proyecto
    "apps.core",
    "apps.clinicas",
    "apps.seguridad",
    "apps.personal",
    "apps.pacientes",
    "apps.atencion",
    "apps.ambulancias",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Debe ir después de AuthenticationMiddleware para ver request.user (sesión/admin).
    # Para JWT, la clínica se fija en TenantJWTAuthentication.
    "apps.core.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de datos PostgreSQL ----------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_requerido("DB_NAME"),
        "USER": env_requerido("DB_USER"),
        "PASSWORD": env_requerido("DB_PASSWORD"),
        "HOST": env_requerido("DB_HOST"),
        "PORT": env_requerido("DB_PORT", cast=int),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 10},
    }
}

# --- Usuario personalizado --------------------------------------------------
AUTH_USER_MODEL = "seguridad.Usuario"

# Backend explícito: usa Usuario.objects (global). El manager filtrado por
# clínica es Usuario.tenant_objects y no interviene en authenticate/get_user.
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalización ---------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = config("TIME_ZONE", default="America/La_Paz")
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos -----------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.core.authentication.TenantJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

# --- Documentación OpenAPI --------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "SaaS Multitenant de Clínicas API",
    "DESCRIPTION": (
        "API REST del SaaS de gestión de clínicas. Sprint 0: modelos, "
        "aislamiento multitenant y datos semilla. Los endpoints de negocio "
        "se incorporan a partir del Sprint 1."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
