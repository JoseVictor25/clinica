"""Pruebas API de S2-03: enfermedades de la historia clínica."""

from datetime import date, timedelta

import pytest
import yaml
from django.utils import timezone

from apps.pacientes.models import (
    Enfermedad,
    HistoriaClinica,
    Paciente,
)
from tests.api.helpers import cliente_autenticado


def url_lista(paciente):
    return f"/api/v1/pacientes/{paciente.pk}/enfermedades/"


def url_detalle(paciente, enfermedad):
    return f"{url_lista(paciente)}{enfermedad.pk}/"


def datos_enfermedad(**cambios):
    datos = {
        "nombre": "Hipertensión arterial",
        "tipo": "CRONICA",
        "severidad": "MODERADA",
        "fecha_deteccion": "2024-06-15",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def historia_a(paciente_a):
    return HistoriaClinica.all_objects.create(paciente=paciente_a)


@pytest.fixture
def enfermedad_a(historia_a):
    return Enfermedad.all_objects.create(
        historia=historia_a,
        **datos_enfermedad(fecha_deteccion=date(2024, 6, 15)),
    )


@pytest.mark.django_db
def test_medico_registra_enfermedad_en_historia_correcta(
    medico_a,
    suscripcion_amplia,
    historia_a,
):
    historias_antes = HistoriaClinica.all_objects.count()

    respuesta = cliente_autenticado(medico_a).post(
        url_lista(historia_a.paciente),
        datos_enfermedad(),
        format="json",
    )

    assert respuesta.status_code == 201
    assert set(respuesta.data) == {
        "id",
        "nombre",
        "tipo",
        "severidad",
        "fecha_deteccion",
    }
    enfermedad = Enfermedad.all_objects.get(pk=respuesta.data["id"])
    assert enfermedad.historia_id == historia_a.pk
    assert HistoriaClinica.all_objects.count() == historias_antes


@pytest.mark.django_db
def test_medico_lista_y_consulta_detalle(
    medico_a,
    suscripcion_amplia,
    enfermedad_a,
):
    cliente = cliente_autenticado(medico_a)

    lista = cliente.get(url_lista(enfermedad_a.historia.paciente))
    detalle = cliente.get(
        url_detalle(enfermedad_a.historia.paciente, enfermedad_a)
    )

    assert lista.status_code == 200
    assert lista.data["count"] == 1
    assert lista.data["results"][0]["id"] == enfermedad_a.pk
    assert detalle.status_code == 200
    assert detalle.data["id"] == enfermedad_a.pk


@pytest.mark.django_db
def test_medico_actualiza_sin_cambiar_historia_ni_paciente(
    medico_a,
    suscripcion_amplia,
    enfermedad_a,
):
    historia_id = enfermedad_a.historia_id
    paciente_id = enfermedad_a.historia.paciente_id

    respuesta = cliente_autenticado(medico_a).patch(
        url_detalle(enfermedad_a.historia.paciente, enfermedad_a),
        {"nombre": "Hipertensión controlada", "severidad": "LEVE"},
        format="json",
    )

    assert respuesta.status_code == 200
    enfermedad_a.refresh_from_db()
    assert enfermedad_a.nombre == "Hipertensión controlada"
    assert enfermedad_a.severidad == "LEVE"
    assert enfermedad_a.historia_id == historia_id
    assert enfermedad_a.historia.paciente_id == paciente_id


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["post", "patch"])
def test_admin_clinica_solo_tiene_lectura(
    metodo,
    admin_a,
    suscripcion_amplia,
    enfermedad_a,
):
    cliente = cliente_autenticado(admin_a)
    if metodo == "post":
        respuesta = cliente.post(
            url_lista(enfermedad_a.historia.paciente),
            datos_enfermedad(),
            format="json",
        )
    else:
        respuesta = cliente.patch(
            url_detalle(enfermedad_a.historia.paciente, enfermedad_a),
            {"nombre": "No autorizado"},
            format="json",
        )

    assert cliente.get(url_lista(enfermedad_a.historia.paciente)).status_code == 200
    assert cliente.get(
        url_detalle(enfermedad_a.historia.paciente, enfermedad_a)
    ).status_code == 200
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "usuario_fixture",
    ["recepcionista_a", "usuario_paciente_a", "conductor_a"],
)
@pytest.mark.parametrize("operacion", ["list", "retrieve", "create", "update"])
def test_roles_no_autorizados_sin_acceso(
    request,
    usuario_fixture,
    operacion,
    suscripcion_amplia,
    enfermedad_a,
):
    usuario = request.getfixturevalue(usuario_fixture)
    cliente = cliente_autenticado(usuario)
    paciente = enfermedad_a.historia.paciente
    if operacion == "list":
        respuesta = cliente.get(url_lista(paciente))
    elif operacion == "retrieve":
        respuesta = cliente.get(url_detalle(paciente, enfermedad_a))
    elif operacion == "create":
        respuesta = cliente.post(
            url_lista(paciente), datos_enfermedad(), format="json"
        )
    else:
        respuesta = cliente.patch(
            url_detalle(paciente, enfermedad_a),
            {"nombre": "No autorizado"},
            format="json",
        )

    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_admin_sistema_y_anonimo_sin_acceso(
    admin_sistema,
    cliente,
    enfermedad_a,
):
    url = url_lista(enfermedad_a.historia.paciente)

    respuesta_admin = cliente_autenticado(admin_sistema).get(url)
    respuesta_anonima = cliente.get(url)

    assert respuesta_admin.status_code == 403
    assert respuesta_admin.data["codigo"] == "permiso_denegado"
    assert respuesta_anonima.status_code == 401
    assert respuesta_anonima.data["codigo"] == "no_autenticado"


@pytest.mark.django_db
def test_suscripcion_vencida_impide_acceso(medico_a, enfermedad_a):
    respuesta = cliente_autenticado(medico_a).get(
        url_lista(enfermedad_a.historia.paciente)
    )

    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_aislamiento_entre_clinicas_es_tenant_safe(
    medico_a,
    suscripcion_amplia,
    clinica_b,
):
    paciente_b = Paciente.all_objects.create(
        clinica=clinica_b,
        ci="PAC-B-ENF",
        nombre="Paciente",
        apellido="Clínica B",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000020",
    )
    historia_b = HistoriaClinica.all_objects.create(paciente=paciente_b)
    enfermedad_b = Enfermedad.all_objects.create(
        historia=historia_b,
        **datos_enfermedad(fecha_deteccion=date(2023, 1, 1)),
    )
    cliente = cliente_autenticado(medico_a)

    respuestas = [
        cliente.get(url_lista(paciente_b)),
        cliente.get(url_detalle(paciente_b, enfermedad_b)),
        cliente.post(url_lista(paciente_b), datos_enfermedad(), format="json"),
        cliente.patch(
            url_detalle(paciente_b, enfermedad_b),
            {"nombre": "Intrusión"},
            format="json",
        ),
    ]

    assert all(respuesta.status_code == 404 for respuesta in respuestas)
    assert all(
        respuesta.data["codigo"] == "no_encontrado"
        for respuesta in respuestas
    )
    enfermedad_b.refresh_from_db()
    assert enfermedad_b.nombre == "Hipertensión arterial"


@pytest.mark.django_db
def test_enfermedad_no_se_puede_usar_con_otro_paciente_del_mismo_tenant(
    medico_a,
    suscripcion_amplia,
    enfermedad_a,
    clinica_configurada,
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-OTRO",
        nombre="Otro",
        apellido="Paciente",
        sexo="M",
        fecha_nacimiento=date(1988, 2, 2),
        telefono="70000021",
    )
    HistoriaClinica.all_objects.create(paciente=otro)
    cliente = cliente_autenticado(medico_a)
    url_incorrecta = url_detalle(otro, enfermedad_a)

    detalle = cliente.get(url_incorrecta)
    edicion = cliente.patch(
        url_incorrecta, {"nombre": "Intrusión"}, format="json"
    )

    assert detalle.status_code == 404
    assert edicion.status_code == 404
    assert detalle.data["codigo"] == "no_encontrado"
    assert edicion.data["codigo"] == "no_encontrado"


@pytest.mark.django_db
def test_paciente_sin_historia_devuelve_conflicto_y_no_la_crea(
    medico_a,
    suscripcion_amplia,
    paciente_a,
):
    assert not HistoriaClinica.all_objects.filter(paciente=paciente_a).exists()

    respuesta = cliente_autenticado(medico_a).get(url_lista(paciente_a))

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "historia_no_disponible"
    assert not HistoriaClinica.all_objects.filter(paciente=paciente_a).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        ({"nombre": "   "}, "datos_invalidos"),
        ({"tipo": "INVALIDA"}, "datos_invalidos"),
        ({"severidad": "INVALIDA"}, "datos_invalidos"),
        (
            {
                "fecha_deteccion": (
                    timezone.localdate() + timedelta(days=1)
                ).isoformat()
            },
            "fecha_deteccion_invalida",
        ),
    ],
)
def test_validaciones_uniformes(
    cambios,
    codigo,
    medico_a,
    suscripcion_amplia,
    historia_a,
):
    respuesta = cliente_autenticado(medico_a).post(
        url_lista(historia_a.paciente),
        datos_enfermedad(**cambios),
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == codigo
    assert "mensaje" in respuesta.data


@pytest.mark.django_db
def test_se_permiten_enfermedades_duplicadas(
    medico_a,
    suscripcion_amplia,
    historia_a,
):
    cliente = cliente_autenticado(medico_a)

    primera = cliente.post(
        url_lista(historia_a.paciente), datos_enfermedad(), format="json"
    )
    segunda = cliente.post(
        url_lista(historia_a.paciente), datos_enfermedad(), format="json"
    )

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert Enfermedad.all_objects.filter(historia=historia_a).count() == 2


@pytest.mark.django_db
def test_filtros_ordenamiento_y_paginacion(
    medico_a,
    suscripcion_amplia,
    historia_a,
):
    Enfermedad.all_objects.create(
        historia=historia_a,
        nombre="Zeta",
        tipo="CRONICA",
        severidad="GRAVE",
        fecha_deteccion=date(2020, 1, 1),
    )
    Enfermedad.all_objects.create(
        historia=historia_a,
        nombre="Alfa",
        tipo="AGUDA",
        severidad="LEVE",
        fecha_deteccion=date(2024, 1, 1),
    )
    cliente = cliente_autenticado(medico_a)
    url = url_lista(historia_a.paciente)

    por_tipo = cliente.get(url, {"tipo": "AGUDA"})
    por_severidad = cliente.get(url, {"severidad": "GRAVE"})
    por_nombre = cliente.get(url, {"ordering": "nombre"})
    predeterminado = cliente.get(url)

    assert por_tipo.data["count"] == 1
    assert por_tipo.data["results"][0]["nombre"] == "Alfa"
    assert por_severidad.data["count"] == 1
    assert por_severidad.data["results"][0]["nombre"] == "Zeta"
    assert [item["nombre"] for item in por_nombre.data["results"]] == [
        "Alfa",
        "Zeta",
    ]
    assert [item["nombre"] for item in predeterminado.data["results"]] == [
        "Alfa",
        "Zeta",
    ]
    assert {"count", "next", "previous", "results"} <= set(
        predeterminado.data
    )


@pytest.mark.django_db
def test_filtros_invalidos_producen_datos_invalidos(
    medico_a,
    suscripcion_amplia,
    historia_a,
):
    cliente = cliente_autenticado(medico_a)
    url = url_lista(historia_a.paciente)

    assert cliente.get(url, {"tipo": "INVALIDO"}).status_code == 400
    assert cliente.get(url, {"severidad": "INVALIDA"}).status_code == 400


@pytest.mark.django_db
def test_delete_y_put_no_estan_expuestos(
    medico_a,
    suscripcion_amplia,
    enfermedad_a,
):
    cliente = cliente_autenticado(medico_a)
    url = url_detalle(enfermedad_a.historia.paciente, enfermedad_a)

    assert cliente.delete(url).status_code == 405
    assert cliente.put(url, datos_enfermedad(), format="json").status_code == 405
    assert Enfermedad.all_objects.filter(pk=enfermedad_a.pk).exists()


@pytest.mark.django_db
def test_openapi_documenta_solo_operaciones_permitidas(cliente):
    respuesta = cliente.get("/api/schema/")
    esquema = yaml.safe_load(respuesta.content)
    lista = esquema["paths"][
        "/api/v1/pacientes/{paciente_id}/enfermedades/"
    ]
    detalle = esquema["paths"][
        "/api/v1/pacientes/{paciente_id}/enfermedades/{enfermedad_id}/"
    ]

    assert respuesta.status_code == 200
    assert {"get", "post"} <= set(lista)
    assert {"get", "patch"} <= set(detalle)
    assert "delete" not in detalle
    assert "put" not in detalle
    contenido = respuesta.content.decode()
    assert "historia_no_disponible" in contenido
    assert "fecha_deteccion_invalida" in contenido
