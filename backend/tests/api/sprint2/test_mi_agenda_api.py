"""Pruebas API de S2-08: agenda personal del médico autenticado."""

from datetime import date, time, timedelta
import json
from unittest.mock import patch

import pytest
from django.test import Client

from apps.atencion.models import Cita, EstadoCita
from apps.clinicas.models import Suscripcion
from apps.core.seed_data import ROL_MEDICO
from apps.pacientes.models import Paciente
from apps.personal.models import Especialidad, Medico, Personal
from apps.seguridad.models import UsuarioRol
from tests.api.helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)


URL = "/api/v1/citas/mi-agenda/"
FECHA = date(2026, 11, 16)


@pytest.fixture
def medico_agenda(clinica_configurada, medico_a):
    _, medico = crear_personal_medico(
        clinica_configurada,
        medico_a,
        ci="CI-AGENDA-001",
        colegiatura="COL-AGENDA-001",
        nombre="Mario",
        apellido="Agenda",
    )
    return medico


@pytest.fixture
def cita_agenda(clinica_configurada, medico_agenda, paciente_a):
    return Cita.all_objects.create(
        clinica=clinica_configurada,
        medico=medico_agenda,
        paciente=paciente_a,
        fecha=FECHA,
        hora=time(8),
        estado=EstadoCita.PROGRAMADA,
        motivo="Control de agenda",
    )


def crear_paciente(clinica, sufijo):
    return Paciente.all_objects.create(
        clinica=clinica,
        ci=f"PAC-AGENDA-{sufijo}",
        nombre="Paciente",
        apellido=f"Agenda {sufijo}",
        sexo="OTRO",
        fecha_nacimiento=date(1990, 1, 1),
        telefono=f"710{sufijo:05d}",
    )


def crear_cita(clinica, medico, paciente, *, fecha=FECHA, hora=time(8), estado=EstadoCita.PROGRAMADA):
    return Cita.all_objects.create(
        clinica=clinica,
        medico=medico,
        paciente=paciente,
        fecha=fecha,
        hora=hora,
        estado=estado,
        motivo=f"Cita {estado}",
    )


@pytest.mark.django_db
def test_medico_vinculado_consulta_solo_su_agenda(
    medico_a,
    suscripcion_amplia,
    cita_agenda,
    clinica_configurada,
    paciente_a,
):
    otro_usuario = crear_usuario_con_rol(
        clinica_configurada, "otro_medico_agenda", ROL_MEDICO
    )
    _, otro_medico = crear_personal_medico(
        clinica_configurada,
        otro_usuario,
        ci="CI-AGENDA-002",
        colegiatura="COL-AGENDA-002",
    )
    ajena = crear_cita(
        clinica_configurada,
        otro_medico,
        paciente_a,
        hora=time(9),
    )

    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    assert [item["id"] for item in respuesta.data["results"]] == [cita_agenda.pk]
    assert ajena.pk not in [item["id"] for item in respuesta.data["results"]]


@pytest.mark.django_db
def test_fecha_predeterminada_usa_timezone_localdate(
    medico_a, suscripcion_amplia, cita_agenda
):
    with patch("apps.atencion.views.timezone.localdate", return_value=FECHA) as localdate:
        respuesta = cliente_autenticado(medico_a).get(URL)

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    assert localdate.call_count >= 1


@pytest.mark.django_db
def test_filtro_fecha_admite_pasado_y_futuro(
    medico_a, suscripcion_amplia, cita_agenda, clinica_configurada, medico_agenda, paciente_a
):
    pasada = crear_cita(
        clinica_configurada,
        medico_agenda,
        paciente_a,
        fecha=FECHA - timedelta(days=1),
        hora=time(9),
    )
    futura = crear_cita(
        clinica_configurada,
        medico_agenda,
        paciente_a,
        fecha=FECHA + timedelta(days=1),
        hora=time(9),
    )
    cliente = cliente_autenticado(medico_a)

    respuesta_pasada = cliente.get(URL, {"fecha": pasada.fecha})
    respuesta_futura = cliente.get(URL, {"fecha": futura.fecha})

    assert [item["id"] for item in respuesta_pasada.data["results"]] == [pasada.pk]
    assert [item["id"] for item in respuesta_futura.data["results"]] == [futura.pk]


@pytest.mark.django_db
@pytest.mark.parametrize("estado", EstadoCita.values)
def test_filtro_estado_y_listado_sin_filtro_incluyen_todos_los_estados(
    estado,
    medico_a,
    suscripcion_amplia,
    clinica_configurada,
    medico_agenda,
):
    creadas = []
    for indice, valor in enumerate(EstadoCita.values):
        paciente = crear_paciente(clinica_configurada, 100 + indice)
        creadas.append(
            crear_cita(
                clinica_configurada,
                medico_agenda,
                paciente,
                hora=time(8 + indice),
                estado=valor,
            )
        )
    cliente = cliente_autenticado(medico_a)

    filtrada = cliente.get(URL, {"fecha": FECHA, "estado": estado})
    completa = cliente.get(URL, {"fecha": FECHA, "page_size": 100})

    assert filtrada.status_code == 200
    assert filtrada.data["count"] == 1
    assert filtrada.data["results"][0]["estado"] == estado
    assert {item["estado"] for item in completa.data["results"]} == set(EstadoCita.values)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("parametros", "campo"),
    [
        ({"fecha": "16/11/2026"}, "fecha"),
        ({"estado": "DESCONOCIDO"}, "estado"),
        ({"medico_id": 999}, "medico_id"),
        ({"paciente_id": 999}, "paciente_id"),
        ({"clinica": 999}, "clinica"),
        ({"ordering": "paciente"}, "ordering"),
        ({"page": 0}, "page"),
        ({"page_size": 101}, "page_size"),
    ],
)
def test_rechaza_filtros_invalidos_o_no_permitidos(
    parametros, campo, medico_a, suscripcion_amplia, medico_agenda
):
    respuesta = cliente_autenticado(medico_a).get(URL, parametros)
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "datos_invalidos"
    assert campo in respuesta.data["detalles"]


@pytest.mark.django_db
def test_ordenamiento_estable_y_parametro_permitido(
    medico_a, suscripcion_amplia, clinica_configurada, medico_agenda
):
    citas = []
    for indice, hora_cita in enumerate((time(9), time(8), time(8))):
        citas.append(
            crear_cita(
                clinica_configurada,
                medico_agenda,
                crear_paciente(clinica_configurada, 200 + indice),
                hora=hora_cita,
                estado=(
                    EstadoCita.CANCELADA
                    if indice == 2
                    else EstadoCita.PROGRAMADA
                ),
            )
        )
    cliente = cliente_autenticado(medico_a)

    predeterminado = cliente.get(URL, {"fecha": FECHA})
    descendente = cliente.get(URL, {"fecha": FECHA, "ordering": "-hora"})

    esperados = sorted(citas, key=lambda cita: (cita.fecha, cita.hora, cita.pk))
    assert [item["id"] for item in predeterminado.data["results"]] == [
        cita.pk for cita in esperados
    ]
    assert descendente.data["results"][0]["hora"].startswith("09:00")


@pytest.mark.django_db
def test_paginacion_no_mezcla_otro_medico(
    medico_a, suscripcion_amplia, clinica_configurada, medico_agenda
):
    otro_usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_paginacion", ROL_MEDICO
    )
    _, otro_medico = crear_personal_medico(
        clinica_configurada,
        otro_usuario,
        ci="CI-AGENDA-PAG",
        colegiatura="COL-AGENDA-PAG",
    )
    propias = []
    for indice in range(3):
        propias.append(
            crear_cita(
                clinica_configurada,
                medico_agenda,
                crear_paciente(clinica_configurada, 300 + indice),
                hora=time(8, indice),
            )
        )
    ajena = crear_cita(
        clinica_configurada,
        otro_medico,
        crear_paciente(clinica_configurada, 399),
        hora=time(8),
    )

    respuesta = cliente_autenticado(medico_a).get(
        URL, {"fecha": FECHA, "page": 2, "page_size": 2}
    )

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 3
    ids = [item["id"] for item in respuesta.data["results"]]
    assert ids == [propias[2].pk]
    assert ajena.pk not in ids


@pytest.mark.django_db
def test_no_expone_datos_clinicos_fuera_del_contrato(
    medico_a, suscripcion_amplia, cita_agenda
):
    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})
    item = respuesta.data["results"][0]
    assert set(item) == {
        "id",
        "paciente_id",
        "paciente_nombre",
        "medico_id",
        "medico_nombre",
        "especialidad_id",
        "especialidad_nombre",
        "fecha",
        "hora",
        "estado",
        "estado_display",
        "modalidad",
        "modalidad_display",
        "link_videollamada",
        "motivo",
        "consulta_id",
        "tiene_consulta",
    }
    assert not ({"historia", "enfermedades", "alergias", "diagnostico", "recetas"} & set(item))


@pytest.mark.django_db
def test_consulta_no_modifica_citas(
    medico_a, suscripcion_amplia, cita_agenda
):
    antes = tuple(
        Cita.all_objects.filter(pk=cita_agenda.pk).values_list(
            "fecha", "hora", "estado", "motivo"
        ).get()
    )
    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})
    despues = tuple(
        Cita.all_objects.filter(pk=cita_agenda.pk).values_list(
            "fecha", "hora", "estado", "motivo"
        ).get()
    )
    assert respuesta.status_code == 200
    assert despues == antes


@pytest.mark.django_db
def test_no_muestra_citas_de_otra_clinica(
    medico_a,
    suscripcion_amplia,
    cita_agenda,
    clinica_b,
):
    from apps.clinicas.services import crear_especialidades_base

    crear_especialidades_base(clinica_b)
    usuario_b = crear_usuario_con_rol(clinica_b, "medico_agenda_b")
    _, medico_b = crear_personal_medico(
        clinica_b,
        usuario_b,
        ci="CI-AGENDA-B",
        colegiatura="COL-AGENDA-B",
    )
    paciente_b = crear_paciente(clinica_b, 400)
    cita_b = crear_cita(clinica_b, medico_b, paciente_b)

    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})

    ids = [item["id"] for item in respuesta.data["results"]]
    assert ids == [cita_agenda.pk]
    assert cita_b.pk not in ids


@pytest.mark.django_db
def test_medico_sin_personal_o_sin_medico_recibe_conflicto(
    medico_a, suscripcion_amplia, clinica_configurada
):
    cliente = cliente_autenticado(medico_a)
    sin_personal = cliente.get(URL, {"fecha": FECHA})
    Personal.all_objects.create(
        clinica=clinica_configurada,
        usuario=medico_a,
        ci="CI-SIN-MEDICO",
        nombre="Sin",
        apellido="Médico",
        telefono="70000000",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    sin_medico = cliente.get(URL, {"fecha": FECHA})

    for respuesta in (sin_personal, sin_medico):
        assert respuesta.status_code == 409
        assert respuesta.data["codigo"] == "medico_no_vinculado"


@pytest.mark.django_db
def test_vinculacion_de_otra_clinica_no_autoriza(
    medico_a, suscripcion_amplia, clinica_b
):
    especialidad = Especialidad.all_objects.create(
        clinica=clinica_b,
        nombre="Especialidad ajena",
    )
    personal = Personal.all_objects.create(
        clinica=clinica_b,
        usuario=medico_a,
        ci="CI-VINCULO-AJENO",
        nombre="Vínculo",
        apellido="Ajeno",
        telefono="70000000",
        cargo="MEDICO",
        fecha_ingreso=date(2025, 1, 1),
    )
    Medico.all_objects.create(
        clinica=clinica_b,
        personal=personal,
        especialidad=especialidad,
        numero_colegiatura="COL-VINCULO-AJENO",
    )

    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_no_vinculado"


@pytest.mark.django_db
@pytest.mark.parametrize("recurso", ["personal", "medico"])
def test_personal_o_medico_inactivo_no_accede(
    recurso, medico_a, suscripcion_amplia, medico_agenda
):
    objeto = medico_agenda.personal if recurso == "personal" else medico_agenda
    objeto.estado = False
    objeto.save(update_fields=["estado"])
    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "medico_inactivo"


@pytest.mark.django_db
def test_rol_medico_inactivo_no_accede(
    medico_a, suscripcion_amplia, medico_agenda
):
    asignacion = UsuarioRol.all_objects.get(usuario=medico_a, rol__nombre=ROL_MEDICO)
    asignacion.rol.estado = False
    asignacion.rol.save(update_fields=["estado"])
    respuesta = cliente_autenticado(medico_a).get(URL, {"fecha": FECHA})
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "usuario_fixture",
    ["admin_a", "recepcionista_a", "usuario_paciente_a", "conductor_a", "admin_sistema"],
)
def test_roles_no_autorizados(usuario_fixture, request, suscripcion_amplia):
    usuario = request.getfixturevalue(usuario_fixture)
    respuesta = cliente_autenticado(usuario).get(URL, {"fecha": FECHA})
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "permiso_denegado"


@pytest.mark.django_db
def test_usuario_anonimo_no_accede(cliente):
    respuesta = cliente.get(URL, {"fecha": FECHA})
    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


@pytest.mark.django_db
def test_clinica_inactiva_y_suscripcion_vencida_no_acceden(
    medico_a, suscripcion_amplia, medico_agenda
):
    cliente = cliente_autenticado(medico_a)
    suscripcion_amplia.estado = Suscripcion.Estado.CANCELADA
    suscripcion_amplia.save(update_fields=["estado"])
    vencida = cliente.get(URL, {"fecha": FECHA})
    assert vencida.status_code == 403
    assert vencida.data["codigo"] == "suscripcion_vencida"

    suscripcion_amplia.estado = Suscripcion.Estado.ACTIVA
    suscripcion_amplia.save(update_fields=["estado"])
    medico_a.clinica.estado = False
    medico_a.clinica.save(update_fields=["estado"])
    inactiva = cliente.get(URL, {"fecha": FECHA})
    assert inactiva.status_code == 403
    assert inactiva.data["codigo"] == "clinica_inactiva"


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["post", "patch", "put", "delete"])
def test_mi_agenda_es_solo_lectura(
    metodo, medico_a, suscripcion_amplia, medico_agenda
):
    respuesta = getattr(cliente_autenticado(medico_a), metodo)(
        URL, {}, format="json"
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_medico_no_obtiene_acceso_a_endpoints_generales(
    medico_a, suscripcion_amplia, cita_agenda
):
    cliente = cliente_autenticado(medico_a)
    assert cliente.get("/api/v1/citas/").status_code == 403
    assert cliente.get(f"/api/v1/citas/{cita_agenda.pk}/").status_code == 403
    assert cliente.post(
        f"/api/v1/citas/{cita_agenda.pk}/confirmar/", {}, format="json"
    ).status_code == 403


@pytest.mark.django_db
def test_openapi_documenta_solo_lectura_de_mi_agenda():
    respuesta = Client().get("/api/schema/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    esquema = json.loads(respuesta.content)
    ruta = esquema["paths"]["/api/v1/citas/mi-agenda/"]
    assert set(ruta) == {"get"}
    operacion = json.dumps(ruta["get"], ensure_ascii=False)
    for texto in (
        "fecha",
        "estado",
        "ordering",
        "medico_id",
        "medico_no_vinculado",
        "medico_inactivo",
    ):
        assert texto in operacion
    assert not any(
        fragmento in path
        for path in esquema["paths"]
        for fragmento in ("atender", "no-asistio", "no_asistio")
    )
