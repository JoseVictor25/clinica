"""Fixtures compartidas por las pruebas del Sprint 0."""

from datetime import date

import pytest

from apps.clinicas.models import Clinica
from apps.core.tenant import limpiar_contexto
from apps.pacientes.models import Paciente
from apps.seguridad.models import Usuario


@pytest.fixture(autouse=True)
def contexto_limpio():
    limpiar_contexto()
    yield
    limpiar_contexto()


@pytest.fixture
def clinica_a(db):
    return Clinica.objects.create(
        nombre="Clínica A",
        direccion="Av. A 1",
        telefono="111111",
        email="a@clinica.local",
        nit="NIT-A",
    )


@pytest.fixture
def clinica_b(db):
    return Clinica.objects.create(
        nombre="Clínica B",
        direccion="Av. B 2",
        telefono="222222",
        email="b@clinica.local",
        nit="NIT-B",
    )


@pytest.fixture
def usuario_a(db, clinica_a):
    return Usuario.objects.create_user(
        username="usuario_a",
        email="usuario_a@clinica.local",
        password="ClaveSegura123!",
        clinica=clinica_a,
    )


@pytest.fixture
def usuario_b(db, clinica_b):
    return Usuario.objects.create_user(
        username="usuario_b",
        email="usuario_b@clinica.local",
        password="ClaveSegura123!",
        clinica=clinica_b,
    )


@pytest.fixture
def admin_sistema(db):
    return Usuario.objects.create_superuser(
        username="admin_sistema_test",
        email="admin_sistema@test.local",
        password="ClaveAdmin123!",
    )


@pytest.fixture
def paciente_a(db, clinica_a):
    return Paciente.all_objects.create(
        clinica=clinica_a,
        ci="CI-A-001",
        nombre="Ana",
        apellido="Paciente",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000001",
        email="ana@test.local",
    )


@pytest.fixture
def paciente_b(db, clinica_b):
    return Paciente.all_objects.create(
        clinica=clinica_b,
        ci="CI-B-001",
        nombre="Beto",
        apellido="Paciente",
        sexo="M",
        fecha_nacimiento=date(1985, 5, 5),
        telefono="70000002",
        email="beto@test.local",
    )
