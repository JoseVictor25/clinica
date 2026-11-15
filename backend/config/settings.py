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
    "rest_framework_simplejwt.token_blacklist",
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
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.api_exceptions.manejador_excepciones",
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": config("LOGIN_THROTTLE_RATE", default="5/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
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
        "API REST del SaaS de gestión de clínicas. Incluye autenticación JWT, "
        "gestión de clínicas, planes, suscripciones, usuarios, roles, personal, "
        "especialidades, médicos y horarios.\n\n"
        "## Formato de error\n\n"
        "Todos los errores usan `{codigo, mensaje, detalles?}`.\n\n"
        "## Códigos de negocio\n\n"
        "- `credenciales_invalidas`: usuario o contraseña incorrectos.\n"
        "- `no_autenticado`: falta el token JWT o es inválido.\n"
        "- `permiso_denegado`: el rol no permite la operación.\n"
        "- `suscripcion_vencida`: la clínica no tiene suscripción vigente.\n"
        "- `limite_usuarios`: se alcanzó `max_usuarios` del plan.\n"
        "- `clinica_inactiva`: la clínica está desactivada (login, token o refresh).\n"
        "- `sin_clinica`: usuario sin clínica que no es administrador del sistema.\n"
        "- `datos_invalidos`: validación de campos (incluye `detalles`).\n"
        "- `password_invalida`: la contraseña no cumple los validadores de Django.\n"
        "- `password_actual_invalida`: la contraseña actual no coincide.\n"
        "- `password_repetida`: la nueva contraseña es igual a la actual.\n"
        "- `refresh_invalido`: el refresh token no es válido o ya fue usado.\n"
        "- `nit_duplicado`, `usuario_duplicado`, `email_duplicado`, "
        "`clinica_duplicada`: conflictos de unicidad.\n"
        "- `limite_usuarios`: capacidad del plan excedida.\n"
        "- `plan_inactivo`, `suscripcion_activa`, `suscripcion_no_vigente`, "
        "`suscripcion_no_activa`, `fechas_invalidas`, `fecha_fin_invalida`: "
        "reglas de suscripciones.\n"
        "- `ultimo_administrador`: no se puede dejar la clínica sin admin activo.\n"
        "- `rol_base_protegido`, `rol_duplicado`, `rol_con_asignaciones`, "
        "`rol_ya_asignado`, `rol_ajeno`, `rol_inactivo`: reglas de roles.\n"
        "- `ci_duplicada`, `personal_ya_es_medico`, `colegiatura_duplicada`, "
        "`especialidad_duplicada`, `especialidad_en_uso`, `horario_solapado`, "
        "`horario_invalido`, `personal_con_medico`, `usuario_ya_vinculado`, "
        "`medico_no_vinculado`: reglas de personal y agenda.\n"
        "- `no_encontrado`: el recurso no existe o pertenece a otra clínica.\n"
        "- `demasiados_intentos`: throttling del login."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
