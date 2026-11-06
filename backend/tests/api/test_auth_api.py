"""Pruebas de autenticación JWT, modo restringido y cambio de contraseña."""

import pytest

from apps.clinicas.models import Clinica
from apps.core.seed_data import ROL_ADMIN_CLINICA
from apps.seguridad.models import Usuario

from .helpers import CLAVE, cliente_autenticado, crear_usuario_con_rol

LOGIN_URL = "/api/v1/auth/login/"


def _login(cliente, username, password=CLAVE):
    return cliente.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
    )


@pytest.mark.django_db
def test_login_exitoso_devuelve_tokens_y_perfil_sin_password(
    cliente, admin_a, suscripcion_a
):
    respuesta = _login(cliente, "admin_a")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["access"]
    assert cuerpo["refresh"]
    assert cuerpo["acceso_restringido"] is False
    assert cuerpo["usuario"]["username"] == "admin_a"
    assert cuerpo["usuario"]["suscripcion_vigente"] is True
    assert "password" not in respuesta.content.decode().lower()


@pytest.mark.django_db
def test_login_credenciales_invalidas(cliente, admin_a, suscripcion_a):
    respuesta = _login(cliente, "admin_a", "ClaveIncorrecta123!")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "credenciales_invalidas"


@pytest.mark.django_db
def test_login_clinica_inactiva(cliente, admin_a, suscripcion_a):
    Clinica.objects.filter(pk=admin_a.clinica_id).update(estado=False)

    respuesta = _login(cliente, "admin_a")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "clinica_inactiva"


@pytest.mark.django_db
def test_login_medico_sin_suscripcion_es_rechazado(
    cliente, clinica_configurada, medico_a
):
    respuesta = _login(cliente, "medico_a")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_admin_sin_suscripcion_entra_en_modo_restringido(
    cliente, admin_a
):
    respuesta = _login(cliente, "admin_a")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["acceso_restringido"] is True
    assert cuerpo["usuario"]["suscripcion_vigente"] is False

    autenticado = cliente_autenticado(admin_a)
    assert autenticado.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_modo_restringido_bloquea_endpoints_de_negocio(
    cliente, admin_a
):
    autenticado = cliente_autenticado(admin_a)

    endpoints = [
        "/api/v1/clinicas/",
        "/api/v1/usuarios/",
        "/api/v1/roles/",
        "/api/v1/usuario-roles/",
        "/api/v1/personal/",
        "/api/v1/especialidades/",
        "/api/v1/medicos/",
        "/api/v1/horarios/",
    ]
    for endpoint in endpoints:
        respuesta = autenticado.get(endpoint)
        assert respuesta.status_code == 403, endpoint
        assert respuesta.json()["codigo"] == "suscripcion_vencida", endpoint


@pytest.mark.django_db
def test_modo_restringido_permite_perfil_planes_y_suscripciones(
    cliente, admin_a
):
    autenticado = cliente_autenticado(admin_a)

    assert autenticado.get("/api/v1/auth/me/").status_code == 200
    assert autenticado.get("/api/v1/planes/").status_code == 200
    assert autenticado.get("/api/v1/suscripciones/").status_code == 200


@pytest.mark.django_db
def test_me_devuelve_roles_y_suscripcion(cliente, admin_a, suscripcion_a):
    respuesta = cliente_autenticado(admin_a).get("/api/v1/auth/me/")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["roles"] == [ROL_ADMIN_CLINICA]
    assert cuerpo["suscripcion_vigente"] is True
    assert cuerpo["acceso_restringido"] is False
    assert "password" not in cuerpo


@pytest.mark.django_db
def test_refresh_rota_el_token_y_el_anterior_queda_en_blacklist(
    cliente, admin_a, suscripcion_a
):
    login = _login(cliente, "admin_a").json()
    refresh_original = login["refresh"]

    respuesta = cliente.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_original},
        format="json",
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["access"]
    assert cuerpo["refresh"] != refresh_original

    repetido = cliente.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_original},
        format="json",
    )
    assert repetido.status_code == 400
    assert repetido.json()["codigo"] == "datos_invalidos"


@pytest.mark.django_db
def test_logout_invalida_el_refresh(cliente, admin_a, suscripcion_a):
    login = _login(cliente, "admin_a").json()
    refresh = login["refresh"]

    autenticado = cliente_autenticado(admin_a)
    respuesta = autenticado.post(
        "/api/v1/auth/logout/", {"refresh": refresh}, format="json"
    )

    assert respuesta.status_code == 204

    repetido = cliente.post(
        "/api/v1/auth/refresh/", {"refresh": refresh}, format="json"
    )
    assert repetido.status_code == 400


@pytest.mark.django_db
def test_cambiar_password_requiere_password_actual(
    cliente, admin_a, suscripcion_a
):
    respuesta = cliente_autenticado(admin_a).post(
        "/api/v1/auth/cambiar-password/",
        {
            "password_actual": "NoEsLaActual123!",
            "password_nueva": "NuevaClaveSegura456!",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "password_actual_invalida"


@pytest.mark.django_db
def test_cambiar_password_aplica_validadores_de_django(
    cliente, admin_a, suscripcion_a
):
    respuesta = cliente_autenticado(admin_a).post(
        "/api/v1/auth/cambiar-password/",
        {"password_actual": CLAVE, "password_nueva": "123"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "password_invalida"


@pytest.mark.django_db
def test_cambiar_password_exitoso_y_solo_para_el_propio_usuario(
    cliente, clinica_configurada, admin_a, suscripcion_a
):
    otro = crear_usuario_con_rol(
        clinica_configurada, "otro_usuario", None, password=CLAVE
    )

    respuesta = cliente_autenticado(admin_a).post(
        "/api/v1/auth/cambiar-password/",
        {
            "password_actual": CLAVE,
            "password_nueva": "NuevaClaveSegura456!",
            "username": "otro_usuario",
        },
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["codigo"] == "password_actualizada"

    otro.refresh_from_db()
    assert otro.check_password(CLAVE)

    assert _login(cliente, "admin_a", CLAVE).status_code == 401
    assert (
        _login(cliente, "admin_a", "NuevaClaveSegura456!").status_code == 200
    )


@pytest.mark.django_db
def test_cambiar_password_requiere_autenticacion(cliente):
    respuesta = cliente.post(
        "/api/v1/auth/cambiar-password/",
        {"password_actual": CLAVE, "password_nueva": "NuevaClaveSegura456!"},
        format="json",
    )

    assert respuesta.status_code == 401


@pytest.mark.django_db
def test_jwt_no_permite_ver_usuarios_de_otra_clinica(
    cliente, clinica_configurada, admin_a, suscripcion_a, usuario_b
):
    autenticado = cliente_autenticado(admin_a)

    detalle = autenticado.get(f"/api/v1/usuarios/{usuario_b.pk}/")
    assert detalle.status_code == 404
    assert detalle.json()["codigo"] == "no_encontrado"

    listado = autenticado.get("/api/v1/usuarios/")
    assert listado.status_code == 200
    ids = [item["id"] for item in listado.json()["results"]]
    assert usuario_b.pk not in ids


@pytest.mark.django_db
def test_usuario_inactivo_no_puede_usar_un_token_emitido(
    cliente, clinica_configurada, admin_a, suscripcion_a
):
    autenticado = cliente_autenticado(admin_a)
    Usuario.objects.filter(pk=admin_a.pk).update(estado=False)

    respuesta = autenticado.get("/api/v1/auth/me/")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"


@pytest.mark.django_db
def test_token_ya_emitido_se_bloquea_al_desactivar_clinica(
    cliente, admin_a, suscripcion_a
):
    autenticado = cliente_autenticado(admin_a)
    Clinica.objects.filter(pk=admin_a.clinica_id).update(estado=False)

    respuesta = autenticado.get("/api/v1/usuarios/")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "clinica_inactiva"


@pytest.mark.django_db
def test_refresh_rechazado_si_clinica_inactiva(
    cliente, admin_a, suscripcion_a
):
    refresh = _login(cliente, "admin_a").json()["refresh"]
    Clinica.objects.filter(pk=admin_a.clinica_id).update(estado=False)

    respuesta = cliente.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh},
        format="json",
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "clinica_inactiva"


@pytest.mark.django_db
def test_reactivar_clinica_restablece_acceso(
    cliente, admin_a, suscripcion_a
):
    autenticado = cliente_autenticado(admin_a)
    Clinica.objects.filter(pk=admin_a.clinica_id).update(estado=False)

    bloqueado = autenticado.get("/api/v1/usuarios/")
    assert bloqueado.status_code == 403
    assert bloqueado.json()["codigo"] == "clinica_inactiva"

    Clinica.objects.filter(pk=admin_a.clinica_id).update(estado=True)

    restablecido = autenticado.get("/api/v1/usuarios/")
    assert restablecido.status_code == 200


@pytest.mark.django_db
def test_admin_sistema_no_se_afecta_por_clinica_inactiva(
    admin_sistema, clinica_a
):
    Clinica.objects.filter(pk=clinica_a.pk).update(estado=False)

    respuesta = cliente_autenticado(admin_sistema).get("/api/v1/clinicas/")

    assert respuesta.status_code == 200
    ids = {item["id"] for item in respuesta.json()["results"]}
    assert clinica_a.pk in ids
