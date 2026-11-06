"""Pruebas de aislamiento multitenant."""

from datetime import date, time

import pytest
from django.utils import timezone

from apps.ambulancias.models import Ambulancia, Traslado
from apps.atencion.models import Cita, Consulta
from apps.clinicas.models import PlanSuscripcion, Suscripcion
from apps.core.exceptions import ClinicaAjena, TenantNoConfigurado
from apps.core.tenant import tenant_context
from apps.pacientes.models import HistoriaClinica, Paciente
from apps.personal.models import Especialidad, Medico, Personal
from apps.seguridad.models import Rol, Usuario


def crear_personal(clinica, ci):
    return Personal.all_objects.create(
        clinica=clinica,
        ci=ci,
        nombre="Nombre",
        apellido="Apellido",
        telefono="70000000",
        cargo="MEDICO",
        fecha_ingreso=date(2020, 1, 1),
    )


@pytest.mark.django_db
def test_manager_sin_contexto_falla_cerrado():
    with pytest.raises(TenantNoConfigurado):
        list(Paciente.objects.all())


@pytest.mark.django_db
def test_manager_con_clinica_none_no_devuelve_datos(paciente_a):
    with tenant_context(None):
        assert Paciente.objects.count() == 0


@pytest.mark.django_db
def test_manager_bypass_ve_todo(paciente_a, paciente_b):
    with tenant_context(bypass=True):
        assert Paciente.objects.count() == 2


@pytest.mark.django_db
def test_all_objects_ve_todo(paciente_a, paciente_b):
    assert Paciente.all_objects.count() == 2


@pytest.mark.django_db
def test_paciente_no_puede_listar_leer_modificar_ni_borrar_otra_clinica(
    clinica_a, paciente_a, paciente_b
):
    with tenant_context(clinica_a):
        assert list(Paciente.objects.all()) == [paciente_a]

        with pytest.raises(Paciente.DoesNotExist):
            Paciente.objects.get(pk=paciente_b.pk)

        assert (
            Paciente.objects.filter(pk=paciente_b.pk).update(nombre="Hackeado")
            == 0
        )
        paciente_b.refresh_from_db()
        assert paciente_b.nombre == "Beto"

        filas_borradas, _ = Paciente.objects.filter(pk=paciente_b.pk).delete()
        assert filas_borradas == 0
        assert Paciente.all_objects.filter(pk=paciente_b.pk).exists()


@pytest.mark.django_db
def test_creacion_asigna_clinica_desde_contexto(clinica_a):
    with tenant_context(clinica_a):
        paciente = Paciente.objects.create(
            ci="CI-AUTO",
            nombre="Auto",
            apellido="Asignado",
            sexo="M",
            fecha_nacimiento=date(1990, 1, 1),
            telefono="1",
        )
    assert paciente.clinica_id == clinica_a.pk


@pytest.mark.django_db
def test_creacion_con_otra_clinica_es_rechazada(clinica_a, clinica_b):
    with tenant_context(clinica_a):
        with pytest.raises(ClinicaAjena):
            Paciente.objects.create(
                clinica=clinica_b,
                ci="CI-B",
                nombre="Intruso",
                apellido="Test",
                sexo="M",
                fecha_nacimiento=date(1990, 1, 1),
                telefono="1",
            )


@pytest.mark.django_db
def test_hijo_filtra_por_clinica_del_padre(
    clinica_a, clinica_b, paciente_a, paciente_b
):
    with tenant_context(clinica_a):
        HistoriaClinica.objects.create(paciente=paciente_a)
    with tenant_context(clinica_b):
        HistoriaClinica.objects.create(paciente=paciente_b)

    with tenant_context(clinica_a):
        assert HistoriaClinica.objects.count() == 1
        assert HistoriaClinica.objects.get().paciente_id == paciente_a.pk
        with pytest.raises(HistoriaClinica.DoesNotExist):
            HistoriaClinica.objects.get(paciente_id=paciente_b.pk)


@pytest.mark.django_db
def test_hijo_no_puede_crearse_con_padre_de_otra_clinica(
    clinica_a, paciente_b
):
    with tenant_context(clinica_a):
        with pytest.raises(ClinicaAjena):
            HistoriaClinica.objects.create(paciente=paciente_b)


@pytest.mark.django_db
def test_usuario_objects_global_y_tenant_objects_filtra(
    clinica_a, usuario_a, usuario_b
):
    # objects es global: lo exige ModelBackend para authenticate/get_user.
    assert set(Usuario.objects.values_list("pk", flat=True)) == {
        usuario_a.pk,
        usuario_b.pk,
    }
    assert (
        Usuario.objects.get_by_natural_key("usuario_b").pk == usuario_b.pk
    )

    with tenant_context(clinica_a):
        assert list(Usuario.tenant_objects.all()) == [usuario_a]
        with pytest.raises(Usuario.DoesNotExist):
            Usuario.tenant_objects.get(pk=usuario_b.pk)
        # all_objects sigue siendo global incluso con tenant activo.
        assert Usuario.all_objects.get(pk=usuario_b.pk) == usuario_b


@pytest.mark.django_db
def test_usuario_tenant_objects_falla_cerrado_sin_contexto():
    with pytest.raises(TenantNoConfigurado):
        list(Usuario.tenant_objects.all())


@pytest.mark.django_db
def test_admin_sistema_bypass_explicito(admin_sistema, paciente_a, paciente_b):
    with tenant_context(bypass=True):
        assert Paciente.objects.count() == 2


@pytest.mark.django_db
def test_modelos_directos_aislados(clinica_a, clinica_b, paciente_a, paciente_b):
    plan = PlanSuscripcion.objects.create(
        nombre="Plan Aislamiento",
        precio="10.00",
        max_usuarios=5,
    )
    Rol.all_objects.create(clinica=clinica_a, nombre="Rol A")
    rol_b = Rol.all_objects.create(clinica=clinica_b, nombre="Rol B")

    personal_a = crear_personal(clinica_a, "P-A")
    personal_b = crear_personal(clinica_b, "P-B")

    especialidad_a = Especialidad.all_objects.create(
        clinica=clinica_a, nombre="Esp A"
    )
    especialidad_b = Especialidad.all_objects.create(
        clinica=clinica_b, nombre="Esp B"
    )

    medico_a = Medico.all_objects.create(
        clinica=clinica_a,
        personal=personal_a,
        especialidad=especialidad_a,
        numero_colegiatura="COL-A",
    )
    medico_b = Medico.all_objects.create(
        clinica=clinica_b,
        personal=personal_b,
        especialidad=especialidad_b,
        numero_colegiatura="COL-B",
    )

    suscripcion_a = Suscripcion.all_objects.create(
        clinica=clinica_a,
        plan=plan,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )
    suscripcion_b = Suscripcion.all_objects.create(
        clinica=clinica_b,
        plan=plan,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )

    cita_a = Cita.all_objects.create(
        clinica=clinica_a,
        medico=medico_a,
        paciente=paciente_a,
        fecha=date(2026, 12, 1),
        hora=time(9, 0),
        motivo="A",
    )
    cita_b = Cita.all_objects.create(
        clinica=clinica_b,
        medico=medico_b,
        paciente=paciente_b,
        fecha=date(2026, 12, 1),
        hora=time(9, 0),
        motivo="B",
    )

    consulta_a = Consulta.all_objects.create(
        clinica=clinica_a,
        medico=medico_a,
        paciente=paciente_a,
        motivo="A",
        observacion="A",
        diagnostico="A",
    )
    consulta_b = Consulta.all_objects.create(
        clinica=clinica_b,
        medico=medico_b,
        paciente=paciente_b,
        motivo="B",
        observacion="B",
        diagnostico="B",
    )

    ambulancia_a = Ambulancia.all_objects.create(
        clinica=clinica_a, matricula="AMB-A", capacidad=2
    )
    ambulancia_b = Ambulancia.all_objects.create(
        clinica=clinica_b, matricula="AMB-B", capacidad=2
    )

    ahora = timezone.now()
    traslado_a = Traslado.all_objects.create(
        clinica=clinica_a,
        ambulancia=ambulancia_a,
        conductor=personal_a,
        paciente=paciente_a,
        motivo="A",
        fecha_salida=ahora,
        lugar_origen="A",
        lugar_destino="B",
    )
    traslado_b = Traslado.all_objects.create(
        clinica=clinica_b,
        ambulancia=ambulancia_b,
        conductor=personal_b,
        paciente=paciente_b,
        motivo="B",
        fecha_salida=ahora,
        lugar_origen="A",
        lugar_destino="B",
    )

    casos = [
        (Rol, clinica_b, rol_b.pk),
        (Personal, clinica_b, personal_b.pk),
        (Especialidad, clinica_b, especialidad_b.pk),
        (Medico, clinica_b, medico_b.pk),
        (Suscripcion, clinica_b, suscripcion_b.pk),
        (Cita, clinica_b, cita_b.pk),
        (Consulta, clinica_b, consulta_b.pk),
        (Ambulancia, clinica_b, ambulancia_b.pk),
        (Traslado, clinica_b, traslado_b.pk),
    ]

    with tenant_context(clinica_a):
        assert Rol.objects.count() == 1
        assert Personal.objects.count() == 1
        assert Especialidad.objects.count() == 1
        assert Medico.objects.count() == 1
        assert Suscripcion.objects.count() == 1
        assert Cita.objects.count() == 1
        assert Consulta.objects.count() == 1
        assert Ambulancia.objects.count() == 1
        assert Traslado.objects.count() == 1

        for modelo, _, pk_b in casos:
            with pytest.raises(modelo.DoesNotExist):
                modelo.objects.get(pk=pk_b)
