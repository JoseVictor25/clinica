"""Pruebas de restricciones e integridad de los modelos."""

from datetime import date, time, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.ambulancias.models import (
    Ambulancia,
    LicenciaConducir,
    Traslado,
)
from apps.atencion.models import Cita
from apps.clinicas.models import Clinica, PlanSuscripcion, Suscripcion
from apps.core.tenant import tenant_context
from apps.pacientes.models import HistoriaClinica, Paciente
from apps.personal.models import (
    Especialidad,
    HorarioAtencion,
    Medico,
    Personal,
)
from apps.seguridad.models import Rol, Usuario, UsuarioRol


def crear_plan(nombre="Plan Test", precio="10.00", max_usuarios=5):
    return PlanSuscripcion.objects.create(
        nombre=nombre,
        precio=precio,
        max_usuarios=max_usuarios,
    )


def crear_personal(clinica, ci="CI-P-001", **extra):
    datos = {
        "clinica": clinica,
        "ci": ci,
        "nombre": "Carlos",
        "apellido": "Médico",
        "telefono": "70000000",
        "cargo": "MEDICO",
        "fecha_ingreso": date(2020, 1, 1),
    }
    datos.update(extra)
    return Personal.all_objects.create(**datos)


def crear_especialidad(clinica, nombre="Medicina General"):
    return Especialidad.all_objects.create(clinica=clinica, nombre=nombre)


def crear_medico(clinica, especialidad, colegiatura="COL-001", **extra):
    personal = extra.pop("personal", None) or crear_personal(clinica)
    return Medico.all_objects.create(
        clinica=clinica,
        personal=personal,
        especialidad=especialidad,
        numero_colegiatura=colegiatura,
        **extra,
    )


def crear_cita(clinica, medico, paciente, estado="PROGRAMADA", **extra):
    datos = {
        "clinica": clinica,
        "medico": medico,
        "paciente": paciente,
        "fecha": date(2026, 12, 1),
        "hora": time(10, 0),
        "estado": estado,
        "motivo": "Consulta",
    }
    datos.update(extra)
    return Cita.all_objects.create(**datos)


@pytest.mark.django_db
def test_nit_clinica_unico(clinica_a):
    with pytest.raises(IntegrityError):
        Clinica.objects.create(
            nombre="Otra",
            direccion="X",
            telefono="1",
            email="x@x.local",
            nit=clinica_a.nit,
        )


@pytest.mark.django_db
def test_plan_max_usuarios_positivo():
    with pytest.raises(IntegrityError):
        crear_plan(max_usuarios=0)


@pytest.mark.django_db
def test_plan_precio_no_negativo():
    with pytest.raises(IntegrityError):
        crear_plan(precio="-1.00")


@pytest.mark.django_db
def test_suscripcion_fechas_invalidas(clinica_a):
    plan = crear_plan()
    with pytest.raises(IntegrityError):
        Suscripcion.all_objects.create(
            clinica=clinica_a,
            plan=plan,
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 1, 1),
        )


@pytest.mark.django_db
def test_una_suscripcion_activa_por_clinica(clinica_a):
    plan = crear_plan()
    Suscripcion.all_objects.create(
        clinica=clinica_a,
        plan=plan,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        estado="ACTIVA",
    )
    with pytest.raises(IntegrityError):
        Suscripcion.all_objects.create(
            clinica=clinica_a,
            plan=plan,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            estado="ACTIVA",
        )


@pytest.mark.django_db
def test_suscripcion_vencida_no_bloquea_activa(clinica_a):
    plan = crear_plan()
    Suscripcion.all_objects.create(
        clinica=clinica_a,
        plan=plan,
        fecha_inicio=date(2025, 1, 1),
        fecha_fin=date(2025, 12, 31),
        estado="VENCIDA",
    )
    Suscripcion.all_objects.create(
        clinica=clinica_a,
        plan=plan,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        estado="ACTIVA",
    )
    assert Suscripcion.all_objects.filter(clinica=clinica_a).count() == 2


@pytest.mark.django_db
def test_password_hasheada(usuario_a):
    assert usuario_a.password != "ClaveSegura123!"
    assert usuario_a.check_password("ClaveSegura123!")


@pytest.mark.django_db
def test_admin_sistema_sin_clinica(admin_sistema):
    assert admin_sistema.clinica is None
    assert admin_sistema.is_superuser is True


@pytest.mark.django_db
def test_usuario_normal_sin_clinica_falla():
    with pytest.raises(IntegrityError):
        Usuario.all_objects.create_user(
            username="sin_clinica",
            email="sin_clinica@test.local",
            password="Clave123!",
        )


@pytest.mark.django_db
def test_rol_unico_por_clinica(clinica_a, clinica_b):
    Rol.all_objects.create(clinica=clinica_a, nombre="Médico")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Rol.all_objects.create(clinica=clinica_a, nombre="Médico")
    Rol.all_objects.create(clinica=clinica_b, nombre="Médico")


@pytest.mark.django_db
def test_usuario_rol_unico_y_misma_clinica(clinica_a, clinica_b, usuario_a, usuario_b):
    rol_a = Rol.all_objects.create(clinica=clinica_a, nombre="Médico")
    rol_b = Rol.all_objects.create(clinica=clinica_b, nombre="Médico")

    UsuarioRol.all_objects.create(usuario=usuario_a, rol=rol_a)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UsuarioRol.all_objects.create(usuario=usuario_a, rol=rol_a)

    asignacion_invalida = UsuarioRol(usuario=usuario_b, rol=rol_a)
    with tenant_context(clinica_b):
        with pytest.raises(ValidationError):
            asignacion_invalida.full_clean()


@pytest.mark.django_db
def test_personal_ci_unica_por_clinica(clinica_a, clinica_b):
    crear_personal(clinica_a, ci="CI-REPETIDA")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            crear_personal(clinica_a, ci="CI-REPETIDA")
    crear_personal(clinica_b, ci="CI-REPETIDA")


@pytest.mark.django_db
def test_medico_colegiatura_unica(clinica_a):
    especialidad = crear_especialidad(clinica_a)
    crear_medico(clinica_a, especialidad, colegiatura="COL-UNICA")
    with pytest.raises(IntegrityError):
        crear_medico(clinica_a, especialidad, colegiatura="COL-UNICA")


@pytest.mark.django_db
def test_horario_horas_invalidas(clinica_a):
    especialidad = crear_especialidad(clinica_a)
    medico = crear_medico(clinica_a, especialidad)
    with pytest.raises(IntegrityError):
        HorarioAtencion.all_objects.create(
            medico=medico,
            dia_semana=0,
            hora_inicio=time(10, 0),
            hora_fin=time(9, 0),
        )


@pytest.mark.django_db
def test_paciente_ci_unica_por_clinica(clinica_a, clinica_b):
    Paciente.all_objects.create(
        clinica=clinica_a,
        ci="CI-PAC-1",
        nombre="Uno",
        apellido="Test",
        sexo="M",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="1",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Paciente.all_objects.create(
                clinica=clinica_a,
                ci="CI-PAC-1",
                nombre="Dos",
                apellido="Test",
                sexo="M",
                fecha_nacimiento=date(1990, 1, 1),
                telefono="2",
            )
    Paciente.all_objects.create(
        clinica=clinica_b,
        ci="CI-PAC-1",
        nombre="Tres",
        apellido="Test",
        sexo="M",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="3",
    )


@pytest.mark.django_db
def test_historia_unica_por_paciente(paciente_a):
    HistoriaClinica.all_objects.create(paciente=paciente_a)
    with pytest.raises(IntegrityError):
        HistoriaClinica.all_objects.create(paciente=paciente_a)


@pytest.mark.django_db
def test_cita_duplicada_activa(clinica_a, paciente_a):
    especialidad = crear_especialidad(clinica_a)
    medico = crear_medico(clinica_a, especialidad)
    crear_cita(clinica_a, medico, paciente_a)
    with pytest.raises(IntegrityError):
        crear_cita(clinica_a, medico, paciente_a)


@pytest.mark.django_db
def test_cita_cancelada_permite_reagendar(clinica_a, paciente_a):
    especialidad = crear_especialidad(clinica_a)
    medico = crear_medico(clinica_a, especialidad)
    crear_cita(clinica_a, medico, paciente_a, estado="CANCELADA")
    crear_cita(clinica_a, medico, paciente_a, estado="PROGRAMADA")
    assert Cita.all_objects.count() == 2


@pytest.mark.django_db
def test_ambulancia_capacidad_positiva(clinica_a):
    with pytest.raises(IntegrityError):
        Ambulancia.all_objects.create(
            clinica=clinica_a,
            matricula="ABC-000",
            capacidad=0,
        )


@pytest.mark.django_db
def test_licencia_fechas_invalidas(clinica_a):
    personal = crear_personal(clinica_a, cargo="CONDUCTOR")
    with pytest.raises(IntegrityError):
        LicenciaConducir.all_objects.create(
            personal=personal,
            numero="LIC-001",
            categoria="B",
            fecha_emision=date(2026, 2, 1),
            fecha_vencimiento=date(2026, 1, 1),
        )


@pytest.mark.django_db
def test_traslado_fechas_invalidas(clinica_a, paciente_a):
    personal = crear_personal(clinica_a, cargo="CONDUCTOR")
    ambulancia = Ambulancia.all_objects.create(
        clinica=clinica_a,
        matricula="XYZ-123",
        capacidad=2,
    )
    ahora = timezone.now()
    with pytest.raises(IntegrityError):
        Traslado.all_objects.create(
            clinica=clinica_a,
            ambulancia=ambulancia,
            conductor=personal,
            paciente=paciente_a,
            motivo="Emergencia",
            fecha_salida=ahora,
            fecha_llegada=ahora - timedelta(hours=1),
            lugar_origen="A",
            lugar_destino="B",
        )
