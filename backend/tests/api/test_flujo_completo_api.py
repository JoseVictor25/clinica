"""Prueba de integración del flujo completo del Sprint 1."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.seed_data import ROL_MEDICO
from apps.personal.models import Especialidad
from apps.seguridad.models import Rol, Usuario

from .helpers import CLAVE, cliente_autenticado

CLINICAS_URL = "/api/v1/clinicas/"
LOGIN_URL = "/api/v1/auth/login/"
SUSCRIPCIONES_URL = "/api/v1/suscripciones/"
USUARIOS_URL = "/api/v1/usuarios/"
PERSONAL_URL = "/api/v1/personal/"
MEDICOS_URL = "/api/v1/medicos/"
HORARIOS_URL = "/api/v1/horarios/"


@pytest.mark.django_db
def test_flujo_completo_de_negocio(admin_sistema, plan_basico):
    hoy = timezone.localdate()

    # 1. El administrador del sistema registra la clínica y su primer admin.
    registro = cliente_autenticado(admin_sistema).post(
        CLINICAS_URL,
        {
            "nombre": "Clínica Flujo",
            "direccion": "Calle 1",
            "telefono": "70000000",
            "email": "flujo@clinica.local",
            "nit": "NIT-FLUJO",
            "admin": {
                "username": "admin_flujo",
                "email": "admin_flujo@clinica.local",
                "password": CLAVE,
            },
        },
        format="json",
    )
    assert registro.status_code == 201, registro.json()
    clinica_id = registro.json()["id"]

    # 2. El administrador de la clínica inicia sesión.
    login = APIClient().post(
        LOGIN_URL,
        {"username": "admin_flujo", "password": CLAVE},
        format="json",
    )
    assert login.status_code == 200, login.json()
    admin = APIClient()
    admin.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}"
    )

    # 3. Contrata el plan.
    suscripcion = admin.post(
        SUSCRIPCIONES_URL,
        {
            "plan_id": plan_basico.pk,
            "fecha_fin": str(hoy + timedelta(days=30)),
        },
        format="json",
    )
    assert suscripcion.status_code == 201, suscripcion.json()

    # 4. Crea un usuario con rol Médico.
    rol_medico = Rol.all_objects.get(
        clinica_id=clinica_id, nombre=ROL_MEDICO
    )
    usuario = admin.post(
        USUARIOS_URL,
        {
            "username": "medico_flujo",
            "email": "medico_flujo@clinica.local",
            "password": CLAVE,
            "roles": [rol_medico.pk],
        },
        format="json",
    )
    assert usuario.status_code == 201, usuario.json()
    usuario_id = usuario.json()["id"]

    # 5. Registra el personal y lo vincula al usuario.
    personal = admin.post(
        PERSONAL_URL,
        {
            "usuario": usuario_id,
            "ci": "CI-FLUJO",
            "nombre": "Marta",
            "apellido": "Flujo",
            "telefono": "70000001",
            "cargo": "MEDICO",
            "fecha_ingreso": str(hoy),
        },
        format="json",
    )
    assert personal.status_code == 201, personal.json()
    personal_id = personal.json()["id"]

    # 6. Registra el médico con una especialidad base.
    especialidad = Especialidad.all_objects.filter(
        clinica_id=clinica_id
    ).first()
    medico = admin.post(
        MEDICOS_URL,
        {
            "personal": personal_id,
            "especialidad": especialidad.pk,
            "numero_colegiatura": "COL-FLUJO",
        },
        format="json",
    )
    assert medico.status_code == 201, medico.json()
    medico_id = medico.json()["id"]

    # 7. Configura un horario de atención.
    horario = admin.post(
        HORARIOS_URL,
        {
            "medico": medico_id,
            "dia_semana": 0,
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
        },
        format="json",
    )
    assert horario.status_code == 201, horario.json()
    horario_id = horario.json()["id"]

    # 8. El médico creado puede entrar y ver su registro y su horario.
    medico_cliente = cliente_autenticado(
        Usuario.all_objects.get(pk=usuario_id)
    )
    medicos = medico_cliente.get(MEDICOS_URL)
    horarios = medico_cliente.get(HORARIOS_URL)

    assert medicos.status_code == 200, medicos.json()
    assert [item["id"] for item in medicos.json()["results"]] == [medico_id]
    assert horarios.status_code == 200, horarios.json()
    assert [item["id"] for item in horarios.json()["results"]] == [horario_id]
