from datetime import timedelta

import pytest
from django.utils import timezone
from apps.pacientes.models import HistoriaClinica, Paciente
from tests.api.helpers import cliente_autenticado

URL = "/api/v1/pacientes/"


def autenticar(usuario):
    return cliente_autenticado(usuario)


@pytest.mark.django_db
def test_requiere_autenticacion(cliente):
    assert cliente.get(URL).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("fixture", ["admin_a", "recepcionista_a", "medico_a"])
def test_roles_permitidos_pueden_listar(request, fixture, suscripcion_amplia):
    assert autenticar(request.getfixturevalue(fixture)).get(URL).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("fixture", ["conductor_a", "usuario_paciente_a"])
def test_roles_no_permitidos_no_pueden_listar(request, fixture, suscripcion_amplia):
    respuesta = autenticar(request.getfixturevalue(fixture)).get(URL)
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_admin_sistema_no_accede(admin_sistema):
    assert autenticar(admin_sistema).get(URL).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("fixture", ["admin_a", "recepcionista_a"])
def test_admin_y_recepcion_crean_paciente(request, fixture, suscripcion_amplia, datos_paciente):
    respuesta = autenticar(request.getfixturevalue(fixture)).post(URL, datos_paciente, format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["clinica"] == request.getfixturevalue(fixture).clinica_id
    assert "usuario" not in respuesta.data


@pytest.mark.django_db
def test_medico_solo_lectura(medico_a, suscripcion_amplia, datos_paciente):
    assert autenticar(medico_a).post(URL, datos_paciente, format="json").status_code == 403


@pytest.mark.django_db
def test_crear_no_acepta_clinica_ajena(admin_a, clinica_b, suscripcion_amplia, datos_paciente):
    datos_paciente["clinica"] = clinica_b.pk
    respuesta = autenticar(admin_a).post(URL, datos_paciente, format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["clinica"] == admin_a.clinica_id


@pytest.mark.django_db
def test_crea_historia_clinica_automaticamente(
    admin_a,
    suscripcion_amplia,
    datos_paciente,
):
    respuesta = autenticar(admin_a).post(
        URL,
        datos_paciente,
        format="json",
    )
    assert respuesta.status_code == 201
    assert HistoriaClinica.all_objects.filter(
        paciente_id=respuesta.data["id"]
    ).count() == 1


@pytest.mark.django_db
def test_ci_duplicada_en_misma_clinica_devuelve_409(admin_a, suscripcion_amplia, paciente_a, datos_paciente):
    respuesta = autenticar(admin_a).post(URL, datos_paciente, format="json")
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "ci_duplicada"


@pytest.mark.django_db
def test_ci_puede_repetirse_en_otra_clinica(admin_b, suscripcion_b, paciente_a, datos_paciente):
    respuesta = autenticar(admin_b).post(URL, datos_paciente, format="json")
    assert respuesta.status_code == 201


@pytest.mark.django_db
def test_fecha_futura_devuelve_codigo_estable(admin_a, suscripcion_amplia, datos_paciente):
    datos_paciente["fecha_nacimiento"] = str(timezone.localdate() + timedelta(days=1))
    respuesta = autenticar(admin_a).post(URL, datos_paciente, format="json")
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "fecha_nacimiento_invalida"


@pytest.mark.django_db
def test_aislamiento_listado_y_detalle(admin_a, admin_b, suscripcion_amplia, suscripcion_b, paciente_a):
    otro = Paciente.all_objects.create(clinica=admin_b.clinica, ci="B-1", nombre="B", apellido="Otro", sexo="M", fecha_nacimiento="1980-01-01", telefono="1")
    cliente = autenticar(admin_a)
    assert [p["id"] for p in cliente.get(URL).data["results"]] == [paciente_a.pk]
    assert cliente.get(f"{URL}{otro.pk}/").status_code == 404


@pytest.mark.django_db
def test_busqueda_filtros_orden_y_paginacion(admin_a, suscripcion_amplia, paciente_a):
    Paciente.all_objects.create(clinica=admin_a.clinica, ci="PAC-002", nombre="Beto", apellido="Álvarez", sexo="M", fecha_nacimiento="1985-01-01", telefono="222", email="beto@example.com", estado=False)
    cliente = autenticar(admin_a)
    assert cliente.get(URL, {"search": "PAC-001"}).data["count"] == 1
    assert cliente.get(URL, {"estado": "false"}).data["results"][0]["ci"] == "PAC-002"
    assert cliente.get(URL, {"sexo": "F"}).data["count"] == 1
    assert cliente.get(URL, {"ordering": "apellido"}).data["results"][0]["ci"] == "PAC-002"
    assert set(cliente.get(URL).data) == {"count", "next", "previous", "results"}


@pytest.mark.django_db
def test_patch_actualiza_y_no_expone_usuario(admin_a, suscripcion_amplia, paciente_a):
    respuesta = autenticar(admin_a).patch(f"{URL}{paciente_a.pk}/", {"nombre": "Nueva", "usuario": 999}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.data["nombre"] == "Nueva"
    assert "usuario" not in respuesta.data


@pytest.mark.django_db
def test_delete_desactiva_y_es_idempotente(recepcionista_a, suscripcion_amplia, paciente_a):
    cliente = autenticar(recepcionista_a)
    assert cliente.delete(f"{URL}{paciente_a.pk}/").status_code == 204
    assert cliente.delete(f"{URL}{paciente_a.pk}/").status_code == 204
    paciente_a.refresh_from_db()
    assert paciente_a.estado is False
    assert Paciente.all_objects.filter(pk=paciente_a.pk).exists()


@pytest.mark.django_db
def test_reactivar_por_patch(admin_a, suscripcion_amplia, paciente_a):
    paciente_a.estado = False
    paciente_a.save(update_fields=["estado"])
    respuesta = autenticar(admin_a).patch(f"{URL}{paciente_a.pk}/", {"estado": True}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.data["estado"] is True


@pytest.mark.django_db
def test_put_no_esta_expuesto(admin_a, suscripcion_amplia, paciente_a, datos_paciente):
    assert autenticar(admin_a).put(f"{URL}{paciente_a.pk}/", datos_paciente, format="json").status_code == 405


@pytest.mark.django_db
def test_openapi_documenta_pacientes(cliente):
    esquema = cliente.get("/api/schema/")
    assert esquema.status_code == 200
    contenido = esquema.content.decode()
    assert "/api/v1/pacientes/" in contenido
    assert "ci_duplicada" in contenido
