"""Pruebas de configuración y registro en el admin."""

import pytest
from django.conf import settings
from django.contrib import admin

from apps.ambulancias.models import (
    Ambulancia,
    Equipamiento,
    LicenciaConducir,
    Traslado,
)
from apps.atencion.models import Cita, Consulta, MedicamentoRecetado, Receta
from apps.clinicas.models import Clinica, PlanSuscripcion, Suscripcion
from apps.pacientes.models import Alergia, Enfermedad, HistoriaClinica, Paciente
from apps.personal.models import Especialidad, HorarioAtencion, Medico, Personal
from apps.seguridad.models import Rol, Usuario, UsuarioRol


def test_auth_user_model_personalizado():
    assert settings.AUTH_USER_MODEL == "seguridad.Usuario"


@pytest.mark.django_db
def test_todos_los_modelos_registrados_en_admin():
    modelos = [
        Clinica,
        PlanSuscripcion,
        Suscripcion,
        Usuario,
        Rol,
        UsuarioRol,
        Personal,
        Especialidad,
        Medico,
        HorarioAtencion,
        Paciente,
        HistoriaClinica,
        Enfermedad,
        Alergia,
        Cita,
        Consulta,
        Receta,
        MedicamentoRecetado,
        Ambulancia,
        Equipamiento,
        LicenciaConducir,
        Traslado,
    ]
    for modelo in modelos:
        assert admin.site.is_registered(modelo), f"{modelo.__name__} no está en admin"
