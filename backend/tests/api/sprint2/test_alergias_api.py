"""Pruebas API de S2-04: alergias de la historia clínica."""

from datetime import date
from unittest.mock import patch

import pytest
import yaml
from django.db import IntegrityError

from apps.core.api_exceptions import Conflicto
from apps.pacientes.models import Alergia, HistoriaClinica, Paciente
from apps.pacientes.services import crear_alergia
from tests.api.helpers import cliente_autenticado


def url_lista(paciente):
    return f"/api/v1/pacientes/{paciente.pk}/alergias/"


def url_detalle(paciente, alergia):
    return f"{url_lista(paciente)}{alergia.pk}/"


@pytest.fixture(autouse=True)
def paciente_base_asignado_al_medico(otorgar_acceso_medico_a_paciente, paciente_a):
    otorgar_acceso_medico_a_paciente(paciente_a)


def datos_alergia(**cambios):
    datos = {
        "nombre": "Penicilina",
        "tipo": "MEDICAMENTO",
        "severidad": "GRAVE",
        "descripcion": "Produce dificultad respiratoria.",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def historia_alergias(paciente_a):
    return HistoriaClinica.all_objects.create(paciente=paciente_a)


@pytest.fixture
def alergia_a(historia_alergias):
    return Alergia.all_objects.create(
        historia=historia_alergias,
        **datos_alergia(),
    )


@pytest.mark.django_db
def test_medico_registra_alergia_en_historia_correcta(
    medico_a,
    suscripcion_amplia,
    historia_alergias,
):
    historias_antes = HistoriaClinica.all_objects.count()

    respuesta = cliente_autenticado(medico_a).post(
        url_lista(historia_alergias.paciente),
        datos_alergia(),
        format="json",
    )

    assert respuesta.status_code == 201
    assert set(respuesta.data) == {
        "id",
        "nombre",
        "tipo",
        "severidad",
        "descripcion",
    }
    alergia = Alergia.all_objects.get(pk=respuesta.data["id"])
    assert alergia.historia_id == historia_alergias.pk
    assert HistoriaClinica.all_objects.count() == historias_antes


@pytest.mark.django_db
def test_medico_lista_y_consulta_detalle(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    cliente = cliente_autenticado(medico_a)

    lista = cliente.get(url_lista(alergia_a.historia.paciente))
    detalle = cliente.get(url_detalle(alergia_a.historia.paciente, alergia_a))

    assert lista.status_code == 200
    assert lista.data["count"] == 1
    assert lista.data["results"][0]["id"] == alergia_a.pk
    assert detalle.status_code == 200
    assert detalle.data["id"] == alergia_a.pk


@pytest.mark.django_db
def test_medico_actualiza_sin_cambiar_historia_ni_paciente(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    historia_id = alergia_a.historia_id
    paciente_id = alergia_a.historia.paciente_id

    respuesta = cliente_autenticado(medico_a).patch(
        url_detalle(alergia_a.historia.paciente, alergia_a),
        {"descripcion": "Reacción cutánea.", "severidad": "MODERADA"},
        format="json",
    )

    assert respuesta.status_code == 200
    alergia_a.refresh_from_db()
    assert alergia_a.descripcion == "Reacción cutánea."
    assert alergia_a.severidad == "MODERADA"
    assert alergia_a.historia_id == historia_id
    assert alergia_a.historia.paciente_id == paciente_id


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["post", "patch"])
def test_admin_clinica_solo_tiene_lectura(
    metodo,
    admin_a,
    suscripcion_amplia,
    alergia_a,
):
    cliente = cliente_autenticado(admin_a)
    paciente = alergia_a.historia.paciente
    if metodo == "post":
        respuesta = cliente.post(
            url_lista(paciente), datos_alergia(nombre="Polen"), format="json"
        )
    else:
        respuesta = cliente.patch(
            url_detalle(paciente, alergia_a),
            {"descripcion": "No autorizado"},
            format="json",
        )

    assert cliente.get(url_lista(paciente)).status_code == 200
    assert cliente.get(url_detalle(paciente, alergia_a)).status_code == 200
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
    alergia_a,
):
    usuario = request.getfixturevalue(usuario_fixture)
    cliente = cliente_autenticado(usuario)
    paciente = alergia_a.historia.paciente
    if operacion == "list":
        respuesta = cliente.get(url_lista(paciente))
    elif operacion == "retrieve":
        respuesta = cliente.get(url_detalle(paciente, alergia_a))
    elif operacion == "create":
        respuesta = cliente.post(
            url_lista(paciente), datos_alergia(nombre="Polen"), format="json"
        )
    else:
        respuesta = cliente.patch(
            url_detalle(paciente, alergia_a),
            {"descripcion": "No autorizado"},
            format="json",
        )

    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_admin_sistema_y_anonimo_sin_acceso(
    admin_sistema,
    cliente,
    alergia_a,
):
    url = url_lista(alergia_a.historia.paciente)

    respuesta_admin = cliente_autenticado(admin_sistema).get(url)
    respuesta_anonima = cliente.get(url)

    assert respuesta_admin.status_code == 403
    assert respuesta_admin.data["codigo"] == "permiso_denegado"
    assert respuesta_anonima.status_code == 401
    assert respuesta_anonima.data["codigo"] == "no_autenticado"


@pytest.mark.django_db
def test_suscripcion_vencida_impide_acceso(medico_a, alergia_a):
    respuesta = cliente_autenticado(medico_a).get(
        url_lista(alergia_a.historia.paciente)
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
        ci="PAC-B-ALERGIA",
        nombre="Paciente",
        apellido="Clínica B",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000030",
    )
    historia_b = HistoriaClinica.all_objects.create(paciente=paciente_b)
    alergia_b = Alergia.all_objects.create(
        historia=historia_b,
        **datos_alergia(),
    )
    cliente = cliente_autenticado(medico_a)

    respuestas = [
        cliente.get(url_lista(paciente_b)),
        cliente.get(url_detalle(paciente_b, alergia_b)),
        cliente.post(
            url_lista(paciente_b), datos_alergia(nombre="Polen"), format="json"
        ),
        cliente.patch(
            url_detalle(paciente_b, alergia_b),
            {"descripcion": "Intrusión"},
            format="json",
        ),
    ]

    assert all(respuesta.status_code == 404 for respuesta in respuestas)
    assert all(
        respuesta.data["codigo"] == "no_encontrado"
        for respuesta in respuestas
    )
    alergia_b.refresh_from_db()
    assert alergia_b.descripcion == "Produce dificultad respiratoria."


@pytest.mark.django_db
def test_alergia_no_se_puede_usar_con_otro_paciente_del_mismo_tenant(
    medico_a,
    suscripcion_amplia,
    alergia_a,
    clinica_configurada,
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-OTRO-ALERGIA",
        nombre="Otro",
        apellido="Paciente",
        sexo="M",
        fecha_nacimiento=date(1988, 2, 2),
        telefono="70000031",
    )
    HistoriaClinica.all_objects.create(paciente=otro)
    cliente = cliente_autenticado(medico_a)
    url_incorrecta = url_detalle(otro, alergia_a)

    detalle = cliente.get(url_incorrecta)
    edicion = cliente.patch(
        url_incorrecta, {"descripcion": "Intrusión"}, format="json"
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
    "cambios",
    [
        {"nombre": ""},
        {"nombre": "   "},
        {"tipo": "INVALIDA"},
        {"severidad": "INVALIDA"},
    ],
)
def test_validaciones_uniformes(
    cambios,
    medico_a,
    suscripcion_amplia,
    historia_alergias,
):
    respuesta = cliente_autenticado(medico_a).post(
        url_lista(historia_alergias.paciente),
        datos_alergia(**cambios),
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"


@pytest.mark.django_db
def test_descripcion_vacia_esta_permitida(
    medico_a,
    suscripcion_amplia,
    historia_alergias,
):
    respuesta = cliente_autenticado(medico_a).post(
        url_lista(historia_alergias.paciente),
        datos_alergia(descripcion=""),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["descripcion"] == ""


@pytest.mark.django_db
def test_nombre_duplicado_devuelve_conflicto(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    respuesta = cliente_autenticado(medico_a).post(
        url_lista(alergia_a.historia.paciente),
        datos_alergia(),
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "alergia_duplicada"


@pytest.mark.django_db
def test_actualizar_a_nombre_duplicado_devuelve_conflicto(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    otra = Alergia.all_objects.create(
        historia=alergia_a.historia,
        **datos_alergia(nombre="Polen", tipo="AMBIENTAL"),
    )

    respuesta = cliente_autenticado(medico_a).patch(
        url_detalle(alergia_a.historia.paciente, otra),
        {"nombre": alergia_a.nombre},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "alergia_duplicada"
    otra.refresh_from_db()
    assert otra.nombre == "Polen"


@pytest.mark.django_db
def test_actualizar_conservando_mismo_nombre_esta_permitido(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    respuesta = cliente_autenticado(medico_a).patch(
        url_detalle(alergia_a.historia.paciente, alergia_a),
        {"nombre": alergia_a.nombre, "descripcion": "Actualizada"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["descripcion"] == "Actualizada"


@pytest.mark.django_db
def test_mismo_nombre_en_historias_distintas_y_semantica_exacta(
    medico_a,
    suscripcion_amplia,
    alergia_a,
    clinica_configurada,
    otorgar_acceso_medico_a_paciente,
):
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        ci="PAC-OTRA-HISTORIA",
        nombre="Otra",
        apellido="Historia",
        sexo="F",
        fecha_nacimiento=date(1991, 3, 3),
        telefono="70000032",
    )
    otra_historia = HistoriaClinica.all_objects.create(paciente=otro)
    otorgar_acceso_medico_a_paciente(otro)
    cliente = cliente_autenticado(medico_a)

    otra_historia_respuesta = cliente.post(
        url_lista(otro), datos_alergia(), format="json"
    )
    distinta_mayuscula = cliente.post(
        url_lista(alergia_a.historia.paciente),
        datos_alergia(nombre="penicilina"),
        format="json",
    )

    assert otra_historia_respuesta.status_code == 201
    assert distinta_mayuscula.status_code == 201
    assert Alergia.all_objects.filter(historia=otra_historia).count() == 1


@pytest.mark.django_db
def test_condicion_de_carrera_se_traduce_por_nombre_de_restriccion(
    historia_alergias,
):
    crear_alergia(historia_alergias, datos_alergia())

    with patch(
        "apps.pacientes.services._existe_alergia",
        return_value=False,
    ):
        with pytest.raises(Conflicto) as error:
            crear_alergia(historia_alergias, datos_alergia())

    assert error.value.codigo == "alergia_duplicada"
    assert Alergia.all_objects.filter(historia=historia_alergias).count() == 1


@pytest.mark.django_db
def test_integrity_error_no_relacionado_se_propaga(historia_alergias):
    fallo = IntegrityError("fallo no relacionado")

    with patch.object(Alergia.all_objects, "create", side_effect=fallo):
        with pytest.raises(IntegrityError) as error:
            crear_alergia(
                historia_alergias,
                datos_alergia(nombre="Mariscos"),
            )

    assert error.value is fallo


@pytest.mark.django_db
def test_filtros_ordenamiento_y_paginacion(
    medico_a,
    suscripcion_amplia,
    historia_alergias,
):
    Alergia.all_objects.create(
        historia=historia_alergias,
        nombre="Zeta",
        tipo="MEDICAMENTO",
        severidad="GRAVE",
        descripcion="",
    )
    Alergia.all_objects.create(
        historia=historia_alergias,
        nombre="Alfa",
        tipo="ALIMENTO",
        severidad="LEVE",
        descripcion="",
    )
    cliente = cliente_autenticado(medico_a)
    url = url_lista(historia_alergias.paciente)

    por_tipo = cliente.get(url, {"tipo": "ALIMENTO"})
    por_severidad = cliente.get(url, {"severidad": "GRAVE"})
    por_nombre = cliente.get(url, {"ordering": "nombre"})
    por_tipo_ordenado = cliente.get(url, {"ordering": "tipo"})
    por_severidad_ordenada = cliente.get(url, {"ordering": "-severidad"})
    predeterminado = cliente.get(url)

    assert por_tipo.data["results"][0]["nombre"] == "Alfa"
    assert por_severidad.data["results"][0]["nombre"] == "Zeta"
    assert [item["nombre"] for item in por_nombre.data["results"]] == [
        "Alfa",
        "Zeta",
    ]
    assert por_tipo_ordenado.status_code == 200
    assert por_severidad_ordenada.status_code == 200
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
    historia_alergias,
):
    cliente = cliente_autenticado(medico_a)
    url = url_lista(historia_alergias.paciente)

    tipo = cliente.get(url, {"tipo": "INVALIDO"})
    severidad = cliente.get(url, {"severidad": "INVALIDA"})

    assert tipo.status_code == 400
    assert tipo.data["codigo"] == "datos_invalidos"
    assert severidad.status_code == 400
    assert severidad.data["codigo"] == "datos_invalidos"


@pytest.mark.django_db
def test_delete_y_put_no_estan_expuestos(
    medico_a,
    suscripcion_amplia,
    alergia_a,
):
    cliente = cliente_autenticado(medico_a)
    url = url_detalle(alergia_a.historia.paciente, alergia_a)

    assert cliente.delete(url).status_code == 405
    assert cliente.put(url, datos_alergia(), format="json").status_code == 405
    assert Alergia.all_objects.filter(pk=alergia_a.pk).exists()


@pytest.mark.django_db
def test_openapi_documenta_solo_operaciones_permitidas(cliente):
    respuesta = cliente.get("/api/schema/")
    esquema = yaml.safe_load(respuesta.content)
    lista = esquema["paths"][
        "/api/v1/pacientes/{paciente_id}/alergias/"
    ]
    detalle = esquema["paths"][
        "/api/v1/pacientes/{paciente_id}/alergias/{alergia_id}/"
    ]

    assert respuesta.status_code == 200
    assert {"get", "post"} <= set(lista)
    assert {"get", "patch"} <= set(detalle)
    assert "delete" not in detalle
    assert "put" not in detalle
    contenido = respuesta.content.decode()
    assert "historia_no_disponible" in contenido
    assert "alergia_duplicada" in contenido
