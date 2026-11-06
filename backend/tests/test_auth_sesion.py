"""Pruebas de regresión de autenticación por sesión y contexto tenant.

Reproducen el fallo original: ModelBackend usaba Usuario._default_manager, que
filtraba por clínica antes de que existiera contexto, provocando
TenantNoConfigurado en la segunda petición (carga del usuario desde la sesión).
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory

from apps.core.middleware import TenantMiddleware
from apps.core.exceptions import TenantNoConfigurado
from apps.core.tenant import (
    esta_en_bypass,
    get_clinica_actual,
    set_clinica_actual,
)
from apps.pacientes.models import Paciente
from apps.seguridad.models import Usuario


def crear_usuario_staff(clinica, username="staff_clinica"):
    return Usuario.objects.create_user(
        username=username,
        email=f"{username}@clinica.local",
        password="ClaveSegura123!",
        clinica=clinica,
        is_staff=True,
    )


# --- ModelBackend sin contexto ------------------------------------------------


@pytest.mark.django_db
def test_modelbackend_authenticate_y_get_user_sin_contexto(admin_sistema):
    backend = ModelBackend()

    usuario = backend.authenticate(
        None, username="admin_sistema_test", password="ClaveAdmin123!"
    )
    assert usuario is not None
    assert usuario.pk == admin_sistema.pk
    assert backend.get_user(admin_sistema.pk).pk == admin_sistema.pk


@pytest.mark.django_db
def test_modelbackend_get_user_de_usuario_con_clinica_sin_contexto(usuario_a):
    backend = ModelBackend()

    usuario = backend.authenticate(
        None, username="usuario_a", password="ClaveSegura123!"
    )
    assert usuario is not None
    assert usuario.pk == usuario_a.pk
    assert backend.get_user(usuario_a.pk).pk == usuario_a.pk


@pytest.mark.django_db
def test_usuario_objects_es_el_default_manager_global():
    assert Usuario._default_manager is Usuario.objects
    assert get_user_model()._default_manager is Usuario.objects


# --- Login por sesión y acceso al admin ---------------------------------------


@pytest.mark.django_db
def test_get_admin_sin_sesion_redirige_al_login():
    respuesta = Client().get("/admin/")

    assert respuesta.status_code == 302
    assert "/admin/login/" in respuesta["Location"]


@pytest.mark.django_db
def test_force_login_admin_sistema_accede_a_admin_y_docs(admin_sistema):
    cliente = Client()
    cliente.force_login(admin_sistema)

    assert cliente.get("/admin/").status_code == 200
    assert cliente.get("/api/docs/").status_code == 200


@pytest.mark.django_db
def test_login_formulario_admin_sistema_y_siguiente_peticion(
    admin_sistema,
):
    cliente = Client()
    respuesta = cliente.post(
        "/admin/login/",
        {
            "username": "admin_sistema_test",
            "password": "ClaveAdmin123!",
            "next": "/admin/",
        },
    )

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/admin/"
    assert cliente.session["_auth_user_id"] == str(admin_sistema.pk)

    # Segunda petición: aquí se cargaba el usuario desde la sesión y fallaba.
    assert cliente.get("/admin/").status_code == 200
    assert cliente.get("/api/docs/").status_code == 200


@pytest.mark.django_db
def test_force_login_usuario_con_clinica_accede_a_admin_y_docs(
    clinica_a,
):
    usuario = crear_usuario_staff(clinica_a)
    cliente = Client()
    cliente.force_login(usuario)

    assert cliente.get("/admin/").status_code == 200
    assert cliente.get("/api/docs/").status_code == 200


@pytest.mark.django_db
def test_login_formulario_usuario_con_clinica_y_siguiente_peticion(
    clinica_a,
):
    usuario = crear_usuario_staff(clinica_a)
    cliente = Client()
    respuesta = cliente.post(
        "/admin/login/",
        {
            "username": "staff_clinica",
            "password": "ClaveSegura123!",
            "next": "/admin/",
        },
    )

    assert respuesta.status_code == 302
    assert cliente.session["_auth_user_id"] == str(usuario.pk)

    assert cliente.get("/admin/").status_code == 200
    assert cliente.get("/api/docs/").status_code == 200


@pytest.mark.django_db
def test_client_login_funciona_para_ambos_tipos_de_usuario(
    clinica_a, admin_sistema
):
    usuario_clinica = crear_usuario_staff(clinica_a)

    cliente = Client()
    assert cliente.login(
        username="admin_sistema_test", password="ClaveAdmin123!"
    )
    assert cliente.get("/admin/").status_code == 200
    cliente.logout()

    assert cliente.login(
        username="staff_clinica", password="ClaveSegura123!"
    )
    assert cliente.session["_auth_user_id"] == str(usuario_clinica.pk)
    assert cliente.get("/admin/").status_code == 200


# --- Contexto por petición y no-fuga entre peticiones --------------------------


@pytest.mark.django_db
def test_middleware_configura_clinica_y_bypass(clinica_a, admin_sistema):
    capturado = {}

    def get_response(request):
        capturado["clinica"] = get_clinica_actual(opcional=True)
        capturado["bypass"] = esta_en_bypass()
        return HttpResponse()

    middleware = TenantMiddleware(get_response)

    request = RequestFactory().get("/")
    request.user = crear_usuario_staff(clinica_a)
    middleware(request)
    assert capturado == {"clinica": clinica_a, "bypass": False}

    request = RequestFactory().get("/")
    request.user = admin_sistema
    middleware(request)
    assert capturado == {"clinica": None, "bypass": True}


@pytest.mark.django_db
def test_no_fuga_contexto_entre_peticiones_en_el_mismo_hilo(clinica_a):
    usuario = crear_usuario_staff(clinica_a)
    capturado = {}

    def get_response(request):
        capturado["clinica"] = get_clinica_actual(opcional=True)
        capturado["bypass"] = esta_en_bypass()
        return HttpResponse()

    middleware = TenantMiddleware(get_response)

    # Petición 1: usuario de la clínica A.
    request = RequestFactory().get("/")
    request.user = usuario
    middleware(request)
    assert capturado == {"clinica": clinica_a, "bypass": False}
    assert get_clinica_actual(opcional=True) is None
    assert esta_en_bypass() is False

    # Petición 2: anónima en el mismo hilo. No debe heredar clínica ni bypass.
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    middleware(request)
    assert capturado == {"clinica": None, "bypass": False}

    # Y el ORM tenant debe fallar cerrado fuera del contexto de la petición.
    with pytest.raises(TenantNoConfigurado):
        list(Paciente.objects.all())


@pytest.mark.django_db
def test_middleware_restaura_contexto_previo_si_la_vista_falla(clinica_a):
    def get_response(request):
        raise RuntimeError("fallo simulado")

    middleware = TenantMiddleware(get_response)
    request = RequestFactory().get("/")
    request.user = crear_usuario_staff(clinica_a)

    with pytest.raises(RuntimeError):
        middleware(request)

    assert get_clinica_actual(opcional=True) is None
    assert esta_en_bypass() is False


# --- Health y raíz ------------------------------------------------------------


@pytest.mark.django_db
def test_health_responde_sin_sesion():
    respuesta = Client().get("/api/health/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


@pytest.mark.django_db
def test_raiz_redirige_a_docs():
    respuesta = Client().get("/")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/api/docs/"


@pytest.mark.django_db
def test_contexto_previo_no_contamina_health(clinica_a):
    set_clinica_actual(clinica_a)

    respuesta = Client().get("/api/health/")

    assert respuesta.status_code == 200
    # contexto_limpio restaura el estado previo al salir de la petición.
    assert get_clinica_actual(opcional=True) == clinica_a
    assert esta_en_bypass() is False
