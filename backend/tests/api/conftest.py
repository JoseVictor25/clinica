"""Fixtures de la API del Sprint 1."""

from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.clinicas.models import PlanSuscripcion
from apps.clinicas.services import (
    crear_especialidades_base,
    crear_roles_base,
)
from apps.core.seed_data import ROL_ADMIN_CLINICA, ROL_MEDICO

from .helpers import crear_suscripcion, crear_usuario_con_rol


@pytest.fixture(autouse=True)
def limpiar_throttle():
    """Evita que el throttling del login se acumule entre pruebas."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def clinica_configurada(clinica_a):
    crear_roles_base(clinica_a)
    crear_especialidades_base(clinica_a)
    return clinica_a


@pytest.fixture
def plan_basico(db):
    return PlanSuscripcion.objects.create(
        nombre="Plan Prueba",
        precio=Decimal("10.00"),
        max_usuarios=2,
        descripcion="Plan de prueba.",
    )


@pytest.fixture
def plan_amplio(db):
    return PlanSuscripcion.objects.create(
        nombre="Plan Amplio",
        precio=Decimal("90.00"),
        max_usuarios=50,
        descripcion="Plan de prueba con capacidad amplia.",
    )


@pytest.fixture
def suscripcion_amplia(clinica_configurada, plan_amplio):
    return crear_suscripcion(clinica_configurada, plan_amplio)


@pytest.fixture
def admin_a(clinica_configurada):
    return crear_usuario_con_rol(
        clinica_configurada, "admin_a", ROL_ADMIN_CLINICA
    )


@pytest.fixture
def admin_b(clinica_b):
    crear_roles_base(clinica_b)
    crear_especialidades_base(clinica_b)
    return crear_usuario_con_rol(
        clinica_b, "admin_b", ROL_ADMIN_CLINICA
    )


@pytest.fixture
def medico_a(clinica_configurada):
    return crear_usuario_con_rol(
        clinica_configurada, "medico_a", ROL_MEDICO
    )


@pytest.fixture
def suscripcion_a(clinica_configurada, plan_basico):
    return crear_suscripcion(clinica_configurada, plan_basico)


@pytest.fixture
def suscripcion_b(clinica_b, plan_basico):
    crear_roles_base(clinica_b)
    crear_especialidades_base(clinica_b)
    return crear_suscripcion(clinica_b, plan_basico)
