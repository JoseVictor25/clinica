"""Pruebas del esquema OpenAPI y de la documentación Swagger."""

import json

import pytest
from django.test import Client

CODIGOS_NEGOCIO = [
    "credenciales_invalidas",
    "no_autenticado",
    "permiso_denegado",
    "suscripcion_vencida",
    "limite_usuarios",
    "clinica_inactiva",
    "datos_invalidos",
    "password_invalida",
    "password_actual_invalida",
    "password_repetida",
    "refresh_invalido",
    "nit_duplicado",
    "usuario_duplicado",
    "email_duplicado",
    "plan_inactivo",
    "suscripcion_activa",
    "suscripcion_no_vigente",
    "suscripcion_no_activa",
    "ultimo_administrador",
    "rol_base_protegido",
    "rol_duplicado",
    "rol_con_asignaciones",
    "ci_duplicada",
    "colegiatura_duplicada",
    "especialidad_duplicada",
    "especialidad_en_uso",
    "horario_solapado",
    "medico_no_vinculado",
    "no_encontrado",
    "demasiados_intentos",
]


@pytest.mark.django_db
def test_esquema_openapi_incluye_bearer_jwt():
    respuesta = Client().get(
        "/api/schema/", HTTP_ACCEPT="application/json"
    )

    assert respuesta.status_code == 200
    esquema = json.loads(respuesta.content)
    esquema_seguridad = esquema["components"]["securitySchemes"]["Bearer"]
    assert esquema_seguridad["type"] == "http"
    assert esquema_seguridad["scheme"] == "bearer"
    assert esquema_seguridad["bearerFormat"] == "JWT"

    operacion = esquema["paths"]["/api/v1/usuarios/"]["get"]
    assert {"Bearer": []} in operacion["security"]

    login = esquema["paths"]["/api/v1/auth/login/"]["post"]
    assert not login.get("security")


@pytest.mark.django_db
def test_esquema_openapi_documenta_codigos_de_negocio():
    respuesta = Client().get(
        "/api/schema/", HTTP_ACCEPT="application/json"
    )
    esquema = json.loads(respuesta.content)
    descripcion = esquema["info"]["description"]

    for codigo in CODIGOS_NEGOCIO:
        assert codigo in descripcion, codigo


@pytest.mark.django_db
def test_esquema_openapi_incluye_endpoints_del_sprint_1():
    respuesta = Client().get(
        "/api/schema/", HTTP_ACCEPT="application/json"
    )
    esquema = json.loads(respuesta.content)
    rutas = set(esquema["paths"])

    esperadas = {
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/me/",
        "/api/v1/auth/cambiar-password/",
        "/api/v1/clinicas/",
        "/api/v1/planes/",
        "/api/v1/suscripciones/",
        "/api/v1/suscripciones/{id}/renovar/",
        "/api/v1/suscripciones/{id}/cambiar-plan/",
        "/api/v1/suscripciones/{id}/cancelar/",
        "/api/v1/usuarios/",
        "/api/v1/roles/",
        "/api/v1/usuario-roles/",
        "/api/v1/personal/",
        "/api/v1/especialidades/",
        "/api/v1/medicos/",
        "/api/v1/horarios/",
    }
    assert esperadas.issubset(rutas)


@pytest.mark.django_db
def test_swagger_ui_responde():
    respuesta = Client().get("/api/docs/")

    assert respuesta.status_code == 200
    assert b"swagger" in respuesta.content.lower()
