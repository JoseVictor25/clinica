"""Pruebas del comando de datos semilla."""

import pytest
from django.core.management import call_command

from apps.clinicas.models import Clinica, PlanSuscripcion
from apps.personal.models import Especialidad
from apps.seguridad.models import Rol, Usuario


@pytest.mark.django_db
def test_semilla_es_idempotente(monkeypatch):
    monkeypatch.setenv("ADMIN_SISTEMA_USERNAME", "admin_semilla")
    monkeypatch.setenv("ADMIN_SISTEMA_EMAIL", "admin_semilla@test.local")
    monkeypatch.setenv("ADMIN_SISTEMA_PASSWORD", "ClaveSemilla123!")
    monkeypatch.setenv("SEED_CREAR_CLINICA_DEMO", "True")
    monkeypatch.setenv("SEED_CLINICA_DEMO_NIT", "NIT-DEMO-TEST")
    monkeypatch.setenv("SEED_CLINICA_DEMO_NOMBRE", "Clinica Demo Test")

    call_command("cargar_semilla", verbosity=0)

    assert PlanSuscripcion.objects.count() == 3
    assert Clinica.objects.count() == 1
    assert Rol.all_objects.count() == 5
    assert Especialidad.all_objects.count() == 8
    assert Usuario.all_objects.filter(username="admin_semilla").count() == 1

    admin = Usuario.all_objects.get(username="admin_semilla")
    assert admin.clinica is None
    assert admin.is_superuser is True
    assert admin.check_password("ClaveSemilla123!")

    call_command("cargar_semilla", verbosity=0)

    assert PlanSuscripcion.objects.count() == 3
    assert Clinica.objects.count() == 1
    assert Rol.all_objects.count() == 5
    assert Especialidad.all_objects.count() == 8
    assert Usuario.all_objects.filter(username="admin_semilla").count() == 1


@pytest.mark.django_db
def test_semilla_sin_clinica_demo_no_crea_roles(monkeypatch):
    monkeypatch.setenv("ADMIN_SISTEMA_USERNAME", "admin_semilla_2")
    monkeypatch.setenv("ADMIN_SISTEMA_EMAIL", "admin_semilla_2@test.local")
    monkeypatch.setenv("ADMIN_SISTEMA_PASSWORD", "ClaveSemilla123!")
    monkeypatch.setenv("SEED_CREAR_CLINICA_DEMO", "False")

    call_command("cargar_semilla", verbosity=0)

    assert PlanSuscripcion.objects.count() == 3
    assert Clinica.objects.count() == 0
    assert Rol.all_objects.count() == 0
    assert Especialidad.all_objects.count() == 0
    assert Usuario.all_objects.filter(username="admin_semilla_2").exists()
