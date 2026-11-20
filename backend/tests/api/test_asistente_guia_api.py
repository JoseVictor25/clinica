"""Pruebas API del Asistente Guía interactivo (Ollama + RBAC + salida estructurada)."""

import json
from unittest.mock import patch
from urllib.error import URLError

import pytest

from apps.seguridad.asistente_services import limpiar_cache_asistente
from apps.core.seed_data import ROL_PACIENTE
from tests.api.helpers import cliente_autenticado, crear_usuario_con_rol


URL = "/api/v1/asistente/consultar/"


@pytest.fixture(autouse=True)
def _limpiar_cache_asistente():
    limpiar_cache_asistente()
    yield
    limpiar_cache_asistente()


class _RespuestaOllamaMock:
    def __init__(self, contenido_dict):
        self._raw = json.dumps(
            {"message": {"role": "assistant", "content": json.dumps(contenido_dict)}}
        ).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.django_db
def test_asistente_rechaza_consulta_vacia(admin_a):
    resp = cliente_autenticado(admin_a).post(
        URL, {"consulta": "   ", "ruta_actual": "/citas"}, format="json"
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_asistente_devuelve_respuesta_estructurada_valida(admin_a):
    respuesta_ia = {
        "explicacion": "Puedes programar una nueva cita desde el módulo Citas.",
        "pasos": ["Abre Citas.", "Pulsa Nueva cita.", "Completa los datos y guarda."],
        "proceso_id": "crear_cita",
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_ia),
    ):
        resp = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Cómo creo una nueva cita?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data == {
        "explicacion": respuesta_ia["explicacion"],
        "pasos": respuesta_ia["pasos"],
        "id_accion": "btn-nueva-cita",
        "id_menu": "nav-citas",
        "ruta_objetivo": "/citas",
    }


@pytest.mark.django_db
def test_asistente_aislamiento_rbac_y_saneamiento_de_ids(clinica_configurada):
    paciente = crear_usuario_con_rol(clinica_configurada, "pac_asistente", ROL_PACIENTE)

    # El modelo intenta devolver un proceso de Admin que el Paciente NO tiene permitido.
    respuesta_alucinada = {
        "explicacion": "Tu perfil no tiene acceso a la gestión de roles.",
        "pasos": [],
        "proceso_id": "gestionar_roles",
    }

    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_alucinada),
    ) as mock_urlopen:
        resp = cliente_autenticado(paciente).post(
            URL,
            {"consulta": "¿Qué puedo hacer en este sistema?", "ruta_actual": "/mi-informacion"},
            format="json",
        )

    assert resp.status_code == 200
    # Verifica que el prompt enviado a Ollama no filtró módulos de Admin al rol Paciente
    # y tampoco expone IDs técnicos data-guia-id al modelo.
    req_enviada = mock_urlopen.call_args.args[0]
    body = json.loads(req_enviada.data.decode("utf-8"))
    prompt_sistema = body["messages"][0]["content"]
    assert "gestionar_roles" not in prompt_sistema
    assert "gestionar_usuarios" not in prompt_sistema
    assert "portal_paciente_citas_estudios" in prompt_sistema
    assert "btn-fila-portal-estudios" not in prompt_sistema
    assert "botón 'Estudios médicos' en la pestaña 'Mis citas'" in prompt_sistema

    # Verifica que el saneamiento anuló los identificadores no autorizados.
    assert resp.data["id_accion"] is None
    assert resp.data["id_menu"] is None
    assert resp.data["ruta_objetivo"] is None


@pytest.mark.django_db
def test_asistente_bloquea_directamente_procesos_no_permitidos_por_rol(
    medico_a, clinica_configurada
):
    paciente = crear_usuario_con_rol(clinica_configurada, "pac_permiso", ROL_PACIENTE)

    with patch("apps.seguridad.asistente_services.urllib_request.urlopen") as mock_urlopen:
        resp_medico = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Cómo creo una cita?", "ruta_actual": "/mi-agenda"},
            format="json",
        )
        resp_paciente = cliente_autenticado(paciente).post(
            URL,
            {"consulta": "¿Cómo creo un nuevo rol?", "ruta_actual": "/mi-informacion"},
            format="json",
        )

    assert mock_urlopen.call_count == 0
    for resp in (resp_medico, resp_paciente):
        assert resp.status_code == 200
        assert "no tienes el permiso necesario" in resp.data["explicacion"].lower()
        assert resp.data["pasos"] == []
        assert resp.data["id_accion"] is None
        assert resp.data["id_menu"] is None
        assert resp.data["ruta_objetivo"] is None


@pytest.mark.django_db
def test_asistente_controla_ollama_no_disponible(medico_a):
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        side_effect=URLError("Connection refused"),
    ):
        resp = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Dónde veo mi agenda?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 503
    assert resp.data["codigo"] == "asistente_no_disponible"


@pytest.mark.django_db
def test_asistente_reemplaza_ids_tecnicos_por_nombres_visuales(admin_a):
    respuesta_con_ids = {
        "explicacion": "Ve a 'nav-citas' y presiona btn-nueva-cita.",
        "pasos": [
            "Abre nav-citas.",
            "Haz clic en `btn-nueva-cita` y completa el formulario.",
        ],
        "proceso_id": "crear_cita",
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_con_ids),
    ):
        resp = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Cómo creo una cita?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 200
    assert "btn-nueva-cita" not in resp.data["explicacion"]
    assert "nav-citas" not in resp.data["explicacion"]
    assert "botón 'Nueva cita'" in resp.data["explicacion"]
    assert all("btn-nueva-cita" not in p and "nav-citas" not in p for p in resp.data["pasos"])
    assert resp.data["id_accion"] == "btn-nueva-cita"
    assert resp.data["id_menu"] == "nav-citas"
    assert resp.data["ruta_objetivo"] == "/citas"


@pytest.mark.django_db
def test_asistente_responde_consulta_informativa_de_modulo(admin_a):
    # Simula una pregunta sobre para qué sirve un módulo donde el modelo responde muy corto.
    respuesta_informativa = {
        "tipo_consulta": "informacion",
        "proceso_id": "gestionar_horarios",
        "explicacion": "Horarios",
        "pasos": [],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_informativa),
    ):
        resp = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Para qué sirve el módulo de horarios?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 200
    assert "franjas horarias" in resp.data["explicacion"]
    assert "30 minutos" in resp.data["explicacion"]
    assert resp.data["pasos"] == []
    assert resp.data["id_accion"] is None
    assert resp.data["id_menu"] == "nav-horarios"
    assert resp.data["ruta_objetivo"] == "/horarios"


@pytest.mark.django_db
def test_asistente_resalta_accion_de_fila_en_tabla(medico_a):
    respuesta_historial = {
        "tipo_consulta": "proceso",
        "proceso_id": "ver_historial_paciente",
        "explicacion": "En el módulo Pacientes puedes abrir el historial desde el botón 'Historial' de la fila del paciente.",
        "pasos": [
            "Abre el módulo Pacientes.",
            "Haz clic en el botón 'Historial' en la fila del paciente.",
        ],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_historial),
    ):
        resp = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Cómo veo el historial de un paciente?", "ruta_actual": "/pacientes"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_accion"] == "btn-fila-paciente-historial"
    assert resp.data["id_menu"] == "nav-pacientes"
    assert resp.data["ruta_objetivo"] == "/pacientes"


@pytest.mark.django_db
def test_asistente_soporta_visor_estudios_y_sala_virtual(medico_a):
    respuesta_visor = {
        "tipo_consulta": "proceso",
        "proceso_id": "visor_estudios_guardar_lectura",
        "explicacion": "Escribe tus conclusiones en el panel derecho y pulsa el botón 'Guardar lectura'.",
        "pasos": [
            "Escribe tu interpretación en 'Observación / Lectura'.",
            "Haz clic en el botón 'Guardar lectura'.",
        ],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_visor),
    ):
        resp = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Cómo guardo la lectura de este estudio?", "ruta_actual": "/estudios/12/visor"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_accion"] == "btn-visor-guardar-lectura"
    assert resp.data["id_menu"] is None
    assert resp.data["ruta_objetivo"] == "/estudios"


@pytest.mark.django_db
def test_asistente_en_visor_expone_herramientas_especificas(medico_a):
    respuesta_regla = {
        "tipo_consulta": "proceso",
        "proceso_id": "visor_regla",
        "explicacion": "Usa el botón 'Regla / Medición' y arrastra sobre la imagen DICOM para medir.",
        "pasos": [
            "Haz clic en el botón 'Regla / Medición'.",
            "Haz clic y arrastra sobre la imagen para trazar la medida.",
        ],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_regla),
    ) as mock_urlopen:
        resp = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Cómo uso la regla para medir?", "ruta_actual": "/estudios/12/visor"},
            format="json",
        )

    assert resp.status_code == 200
    req_enviada = mock_urlopen.call_args.args[0]
    body = json.loads(req_enviada.data.decode("utf-8"))
    prompt_sistema = body["messages"][0]["content"]
    assert "visor_regla" in prompt_sistema
    assert len(body["format"]["properties"]["proceso_id"]["enum"]) <= 7
    assert resp.data["id_accion"] == "btn-visor-regla"
    assert resp.data["ruta_objetivo"] == "/estudios"


@pytest.mark.django_db
def test_asistente_en_mi_suscripcion_resalta_accion_en_el_mismo_modulo(admin_a):
    respuesta_cambiar = {
        "tipo_consulta": "proceso",
        "proceso_id": "cambiar_plan_suscripcion",
        "explicacion": "En esta pantalla puedes cambiar tu plan pulsando el botón 'Cambiar plan'.",
        "pasos": [
            "Haz clic en el botón 'Cambiar plan'.",
            "Selecciona el nuevo plan y confirma.",
        ],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_cambiar),
    ):
        resp = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Cómo cambio de plan?", "ruta_actual": "/suscripciones"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_accion"] == "btn-suscripcion-cambiar-plan"
    assert resp.data["id_menu"] == "nav-suscripciones"
    assert resp.data["ruta_objetivo"] == "/suscripciones"


@pytest.mark.django_db
def test_asistente_conoce_pestana_activa_en_mi_informacion(clinica_configurada):
    paciente = crear_usuario_con_rol(clinica_configurada, "pac_pestana", ROL_PACIENTE)
    respuesta = {
        "tipo_consulta": "proceso",
        "proceso_id": "portal_paciente_citas_estudios",
        "explicacion": "Ya estás en 'Mis citas'; pulsa el botón 'Estudios médicos' en la cita deseada.",
        "pasos": ["En la tarjeta de tu cita, haz clic en 'Estudios médicos'."],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ) as mock_urlopen:
        resp = cliente_autenticado(paciente).post(
            URL,
            {
                "consulta": "¿Cómo subo un estudio médico?",
                "ruta_actual": "/mi-informacion | pestaña: Mis citas",
            },
            format="json",
        )

    assert resp.status_code == 200
    prompt = json.loads(mock_urlopen.call_args.args[0].data.decode("utf-8"))["messages"][0]["content"]
    assert "pestaña activa 'Mis citas'" in prompt
    assert resp.data["id_accion"] == "btn-fila-portal-estudios"
    assert resp.data["ruta_objetivo"] == "/mi-informacion"


@pytest.mark.django_db
def test_asistente_corrige_proceso_erroneo_cuando_explicacion_cita_otro_control(clinica_configurada):
    paciente = crear_usuario_con_rol(clinica_configurada, "pac_corrige", ROL_PACIENTE)
    # Simula que el modelo redacta bien sobre 'Estudios médicos' pero elige erróneamente mi_cuenta_password.
    respuesta_desalineada = {
        "tipo_consulta": "proceso",
        "proceso_id": "mi_cuenta_password",
        "explicacion": "Para subir tus estudios médicos a una cita, entra a 'Mi información' y pulsa el botón 'Estudios médicos' en tu cita.",
        "pasos": [],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta_desalineada),
    ):
        resp = cliente_autenticado(paciente).post(
            URL,
            {
                "consulta": "tengo unos estudios medicos y tengo una cita como le puedo pasar esos estudios a una cita",
                "ruta_actual": "/mi-informacion | pestaña: Mis citas",
            },
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_accion"] == "btn-fila-portal-estudios"
    assert resp.data["id_menu"] == "nav-mi-informacion"
    assert resp.data["ruta_objetivo"] == "/mi-informacion"
    assert all("contraseña" not in paso.lower() for paso in resp.data["pasos"])


@pytest.mark.django_db
def test_asistente_no_agrega_pasos_en_pregunta_de_regla_o_permiso(clinica_configurada):
    paciente = crear_usuario_con_rol(clinica_configurada, "pac_regla", ROL_PACIENTE)
    # Aunque el modelo clasifique erróneamente como 'proceso' y deje pasos=[],
    # no se deben inyectar pasos_base ante una pregunta de regla ("si puedo...") o respuesta negativa.
    respuesta = {
        "tipo_consulta": "proceso",
        "proceso_id": "portal_paciente_citas_estudios",
        "explicacion": "No es posible subir estudios médicos a una cita que ya está en estado ATENDIDA; solo se permite mientras la cita sigue abierta.",
        "pasos": [],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ):
        resp = cliente_autenticado(paciente).post(
            URL,
            {
                "consulta": "puedo subir estudios medicos a una cita en estado ATENDIDO",
                "ruta_actual": "/mi-informacion | pestaña: Mis citas",
            },
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["pasos"] == []
    assert resp.data["id_accion"] is None


@pytest.mark.django_db
def test_asistente_en_mi_agenda_no_confunde_verbo_ver_con_pacientes(medico_a):
    respuesta = {
        "tipo_consulta": "proceso",
        "proceso_id": "ver_detalle_cita_agenda",
        "explicacion": "Para ver la información de una cita en Mi agenda, haz clic en el botón 'Ver' de la fila de la cita.",
        "pasos": [],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ):
        resp = cliente_autenticado(medico_a).post(
            URL,
            {
                "consulta": "como puedo ver la informacion de un cita?",
                "ruta_actual": "/mi-agenda",
            },
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_accion"] == "btn-fila-agenda-ver"
    assert resp.data["id_menu"] == "nav-mi-agenda"
    assert resp.data["ruta_objetivo"] == "/mi-agenda"


@pytest.mark.django_db
def test_asistente_recorta_especulacion_tras_rechazo_de_permiso(medico_a):
    respuesta = {
        "tipo_consulta": "informacion",
        "proceso_id": "gestionar_horarios",
        "explicacion": "Tu rol actual no tiene permiso para esa acción. Este proceso pertenece al módulo 'Horarios'.",
        "pasos": ["Abre Horarios."],
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ):
        resp = cliente_autenticado(medico_a).post(
            URL,
            {"consulta": "¿Puedo modificar la facturación de la clínica?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["explicacion"] == "Tu rol actual no tiene permiso para esa acción."
    assert resp.data["pasos"] == []
    assert resp.data["id_accion"] is None
    assert resp.data["id_menu"] is None


@pytest.mark.django_db
def test_asistente_reutiliza_cache_en_consultas_repetidas(admin_a):
    respuesta = {
        "tipo_consulta": "proceso",
        "proceso_id": "cambiar_plan_suscripcion",
        "explicacion": "Usa el botón 'Cambiar plan' en esta pantalla para cambiar tu suscripción.",
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ) as mock_urlopen:
        r1 = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Cómo cambio de plan?", "ruta_actual": "/suscripciones"},
            format="json",
        )
        r2 = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "como cambio de plan", "ruta_actual": "/suscripciones"},
            format="json",
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_urlopen.call_count == 1
    assert r1.data == r2.data
    assert len(r1.data["pasos"]) > 0


@pytest.mark.django_db
def test_asistente_infiere_menu_cuando_proceso_no_tiene_id_accion(admin_a):
    respuesta = {
        "tipo_consulta": "proceso",
        "proceso_id": "ninguno",
        "explicacion": "Puedes ver la información de la clínica haciendo clic en la opción 'Mi clínica' del menú lateral.",
    }
    with patch(
        "apps.seguridad.asistente_services.urllib_request.urlopen",
        return_value=_RespuestaOllamaMock(respuesta),
    ):
        resp = cliente_autenticado(admin_a).post(
            URL,
            {"consulta": "¿Dónde puedo ver la información de la clínica?", "ruta_actual": "/"},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.data["id_menu"] == "nav-mi-clinica"
    assert resp.data["ruta_objetivo"] == "/mi-clinica"
