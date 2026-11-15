"""Pruebas de clínicas, planes y suscripciones."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.clinicas.models import Clinica, PlanSuscripcion, Suscripcion
from apps.core.seed_data import (
    ESPECIALIDADES_BASE,
    ROL_ADMIN_CLINICA,
    ROLES_BASE,
)
from apps.personal.models import Especialidad
from apps.seguridad.models import Rol, Usuario, UsuarioRol

from .helpers import cliente_autenticado, crear_suscripcion, crear_usuario_con_rol

CLINICAS_URL = "/api/v1/clinicas/"
PLANES_URL = "/api/v1/planes/"
SUSCRIPCIONES_URL = "/api/v1/suscripciones/"


def _payload_clinica(nit="NIT-NUEVA", username="admin_nuevo"):
    return {
        "nombre": "Clínica Nueva",
        "direccion": "Calle 1",
        "telefono": "123456",
        "email": "nueva@clinica.local",
        "nit": nit,
        "admin": {
            "username": username,
            "email": f"{username}@clinica.local",
            "password": "ClaveSegura123!",
        },
    }


@pytest.mark.django_db
def test_admin_sistema_registra_clinica_y_provisiona_datos_base(
    admin_sistema,
):
    respuesta = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL, _payload_clinica(), format="json"
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["nit"] == "NIT-NUEVA"
    assert "password" not in respuesta.content.decode().lower()

    clinica = Clinica.objects.get(nit="NIT-NUEVA")
    assert Rol.all_objects.filter(clinica=clinica).count() == len(ROLES_BASE)
    assert (
        Especialidad.all_objects.filter(clinica=clinica).count()
        == len(ESPECIALIDADES_BASE)
    )

    admin = Usuario.all_objects.get(username="admin_nuevo")
    assert admin.clinica_id == clinica.pk
    assert admin.is_staff is False
    assert admin.is_superuser is False
    assert UsuarioRol.all_objects.filter(
        usuario=admin, rol__nombre=ROL_ADMIN_CLINICA
    ).exists()


@pytest.mark.django_db
def test_bootstrap_no_valida_max_usuarios_ni_suscripcion(admin_sistema):
    # La clínica parte sin suscripción: aun así el primer admin se crea.
    respuesta = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL, _payload_clinica(), format="json"
    )

    assert respuesta.status_code == 201
    assert Usuario.all_objects.filter(username="admin_nuevo").exists()
    assert not Suscripcion.all_objects.exists()


@pytest.mark.django_db
def test_registrar_clinica_con_nit_duplicado(admin_sistema, clinica_a):
    respuesta = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL, _payload_clinica(nit=clinica_a.nit), format="json"
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "nit_duplicado"


@pytest.mark.django_db
def test_registrar_clinica_con_usuario_duplicado(
    admin_sistema, admin_a
):
    respuesta = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL,
        _payload_clinica(username=admin_a.username),
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "usuario_duplicado"


@pytest.mark.django_db
def test_registrar_clinica_con_password_invalida(admin_sistema):
    payload = _payload_clinica()
    payload["admin"]["password"] = "123"

    respuesta = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL, payload, format="json"
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert not Clinica.objects.filter(nit="NIT-NUEVA").exists()


@pytest.mark.django_db
def test_admin_de_clinica_no_puede_registrar_clinicas(
    admin_a, suscripcion_a
):
    respuesta = cliente_autenticado(admin_a).post(
        CLINICAS_URL, _payload_clinica(), format="json"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_admin_de_clinica_solo_ve_su_clinica(
    admin_a, clinica_b, suscripcion_a
):
    autenticado = cliente_autenticado(admin_a)

    listado = autenticado.get(CLINICAS_URL)
    assert listado.status_code == 200
    ids = [item["id"] for item in listado.json()["results"]]
    assert ids == [admin_a.clinica_id]

    detalle = autenticado.get(f"{CLINICAS_URL}{clinica_b.pk}/")
    assert detalle.status_code == 404


@pytest.mark.django_db
def test_admin_sistema_ve_todas_las_clinicas(
    admin_sistema, clinica_a, clinica_b
):
    respuesta = cliente_autenticado(admin_sistema).get(CLINICAS_URL)

    assert respuesta.status_code == 200
    ids = {item["id"] for item in respuesta.json()["results"]}
    assert {clinica_a.pk, clinica_b.pk}.issubset(ids)


@pytest.mark.django_db
def test_admin_sistema_desactiva_clinica_con_soft_delete(
    admin_sistema, clinica_a
):
    respuesta = cliente_autenticado(admin_sistema).delete(
        f"{CLINICAS_URL}{clinica_a.pk}/"
    )

    assert respuesta.status_code == 204
    clinica_a.refresh_from_db()
    assert clinica_a.estado is False


@pytest.mark.django_db
def test_planes_visibles_para_admin_sin_suscripcion(admin_a, plan_basico):
    respuesta = cliente_autenticado(admin_a).get(PLANES_URL)

    assert respuesta.status_code == 200
    assert respuesta.json()["results"][0]["nombre"] == "Plan Prueba"


@pytest.mark.django_db
def test_solo_admin_sistema_gestiona_planes(admin_sistema, admin_a):
    payload = {
        "nombre": "Plan Premium Test",
        "precio": "30.00",
        "max_usuarios": 10,
        "descripcion": "Plan de prueba.",
    }

    assert (
        cliente_autenticado(admin_a)
        .post(PLANES_URL, payload, format="json")
        .status_code
        == 403
    )

    creado = cliente_autenticado(admin_sistema).post(
        PLANES_URL, payload, format="json"
    )
    assert creado.status_code == 201


@pytest.mark.django_db
def test_contratar_renovar_cambiar_y_cancelar_suscripcion(
    admin_a, clinica_configurada, plan_basico
):
    autenticado = cliente_autenticado(admin_a)
    hoy = timezone.localdate()

    assert autenticado.get(SUSCRIPCIONES_URL).json()["results"] == []

    creada = autenticado.post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan_basico.pk,
            "fecha_inicio": str(hoy),
            "fecha_fin": str(hoy + timedelta(days=30)),
        },
        format="json",
    )
    assert creada.status_code == 201
    suscripcion_id = creada.json()["id"]

    duplicada = autenticado.post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan_basico.pk,
            "fecha_fin": str(hoy + timedelta(days=60)),
        },
        format="json",
    )
    assert duplicada.status_code == 409
    assert duplicada.json()["codigo"] == "suscripcion_activa"

    renovada = autenticado.post(
        f"{SUSCRIPCIONES_URL}{suscripcion_id}/renovar/",
        {"nueva_fecha_fin": str(hoy + timedelta(days=90))},
        format="json",
    )
    assert renovada.status_code == 200

    anterior = autenticado.post(
        f"{SUSCRIPCIONES_URL}{suscripcion_id}/renovar/",
        {"nueva_fecha_fin": str(hoy + timedelta(days=80))},
        format="json",
    )
    assert anterior.status_code == 400
    assert anterior.json()["codigo"] == "fecha_fin_invalida"

    plan_nuevo = PlanSuscripcion.objects.create(
        nombre="Plan Superior",
        precio=Decimal("50.00"),
        max_usuarios=10,
    )
    cambiada = autenticado.post(
        f"{SUSCRIPCIONES_URL}{suscripcion_id}/cambiar-plan/",
        {
            "plan_id": plan_nuevo.pk,
            "fecha_inicio": str(hoy),
            "fecha_fin": str(hoy + timedelta(days=120)),
        },
        format="json",
    )
    assert cambiada.status_code == 200
    assert cambiada.json()["plan"] == plan_nuevo.pk

    nueva_id = cambiada.json()["id"]
    cancelada = autenticado.post(
        f"{SUSCRIPCIONES_URL}{nueva_id}/cancelar/", {}, format="json"
    )
    assert cancelada.status_code == 200
    assert cancelada.json()["estado"] == Suscripcion.Estado.CANCELADA

    repetida = autenticado.post(
        f"{SUSCRIPCIONES_URL}{nueva_id}/cancelar/", {}, format="json"
    )
    assert repetida.status_code == 409
    assert repetida.json()["codigo"] == "suscripcion_no_activa"


@pytest.mark.django_db
def test_contratar_plan_sin_capacidad_para_usuarios_activos(
    admin_a, clinica_configurada
):
    crear_usuario_con_rol(clinica_configurada, "usuario_extra")
    plan_pequeno = PlanSuscripcion.objects.create(
        nombre="Plan Mínimo",
        precio=Decimal("1.00"),
        max_usuarios=1,
    )

    respuesta = cliente_autenticado(admin_a).post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan_pequeno.pk,
            "fecha_fin": str(timezone.localdate() + timedelta(days=30)),
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "limite_usuarios"
    assert respuesta.json()["detalles"]["usuarios_activos"] == 2


@pytest.mark.django_db
def test_contratar_plan_inactivo(admin_a, clinica_configurada):
    plan = PlanSuscripcion.objects.create(
        nombre="Plan Inactivo",
        precio=Decimal("1.00"),
        max_usuarios=10,
        activo=False,
    )

    respuesta = cliente_autenticado(admin_a).post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan.pk,
            "fecha_fin": str(timezone.localdate() + timedelta(days=30)),
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "plan_inactivo"


@pytest.mark.django_db
def test_no_renovar_suscripcion_vencida(
    admin_a, clinica_configurada, plan_basico
):
    vencida = crear_suscripcion(
        clinica_configurada,
        plan_basico,
        dias=-5,
        estado=Suscripcion.Estado.VENCIDA,
    )

    respuesta = cliente_autenticado(admin_a).post(
        f"{SUSCRIPCIONES_URL}{vencida.pk}/renovar/",
        {"nueva_fecha_fin": str(timezone.localdate() + timedelta(days=30))},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "suscripcion_no_vigente"


@pytest.mark.django_db
def test_admin_sistema_no_contrata_suscripciones(admin_sistema, plan_basico):
    respuesta = cliente_autenticado(admin_sistema).post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan_basico.pk,
            "fecha_fin": str(timezone.localdate() + timedelta(days=30)),
        },
        format="json",
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "permiso_denegado"
