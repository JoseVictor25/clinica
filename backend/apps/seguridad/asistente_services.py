"""Servicio de integración con Ollama (JSON estructurado + aislamiento RBAC)."""

import json
import re
import time
import unicodedata
from urllib import error as urllib_error, request as urllib_request

from django.conf import settings

from apps.core.api_exceptions import ErrorNegocio, PermisoDenegado
from apps.seguridad.models import UsuarioRol

from .asistente_catalogo import (
    NOMBRES_VISUALES_UI,
    REGLAS_PERMISO_PROCESOS,
    filtrar_catalogo_por_roles,
)


_CACHE_RESPUESTAS = {}
_CACHE_TTL_SEGUNDOS = 300
_CACHE_MAX_ENTRADAS = 128


def limpiar_cache_asistente():
    _CACHE_RESPUESTAS.clear()


class AsistenteNoDisponible(ErrorNegocio):
    status_code = 503
    codigo = "asistente_no_disponible"
    default_detail = "El asistente guía no está disponible temporalmente."


def _construir_esquema_ollama(catalogo):
    # El modelo solo genera tipo_consulta, proceso_id y explicacion; los pasos se
    # resuelven determinísticamente desde el catálogo para acelerar ~2x la respuesta en CPU.
    return {
        "type": "object",
        "properties": {
            "tipo_consulta": {
                "type": "string",
                "enum": ["informacion", "proceso"],
            },
            "proceso_id": {
                "type": "string",
                "enum": [item["id"] for item in catalogo] + ["ninguno"],
            },
            "explicacion": {"type": "string"},
        },
        "required": ["tipo_consulta", "proceso_id", "explicacion"],
        "additionalProperties": False,
    }


def obtener_roles_activos_usuario(usuario):
    return list(
        UsuarioRol.all_objects.filter(
            usuario=usuario,
            rol__estado=True,
        ).values_list("rol__nombre", flat=True)
    )


_STOPWORDS_ES = frozenset(
    {
        "como",
        "cual",
        "cuales",
        "donde",
        "para",
        "porque",
        "puedo",
        "quiero",
        "necesito",
        "hacer",
        "sobre",
        "este",
        "esta",
        "esto",
        "ese",
        "esa",
        "modulo",
        "opcion",
        "pantalla",
        "seccion",
        "boton",
        "sirve",
        "funciona",
        "usar",
        "una",
        "uno",
        "unos",
        "unas",
        "los",
        "las",
        "del",
        "con",
        "por",
        "sin",
        "mis",
        "que",
        "son",
        "hay",
    }
)


def _normalizar_texto_plano(texto):
    sin_acentos = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", (texto or "").lower())
        if not unicodedata.combining(ch)
    )
    sin_puntuacion = re.sub(r"[^a-z0-9\s]", " ", sin_acentos)
    return re.sub(r"\s+", " ", sin_puntuacion).strip()


def _verificar_permiso_consulta(consulta, roles):
    """Devuelve la descripción de la acción si la consulta pide un proceso no autorizado para el rol."""

    texto = _normalizar_texto_plano(consulta)
    if not texto:
        return None
    roles_set = set(roles)
    for regla in REGLAS_PERMISO_PROCESOS:
        if any(re.search(patron, texto) for patron in regla["patrones"]):
            if not roles_set.intersection(regla["roles_permitidos"]):
                return regla["accion"]
    return None


def _normalizar_tokens(texto):
    sin_acentos = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", (texto or "").lower())
        if not unicodedata.combining(ch)
    )
    return [
        tok
        for tok in re.findall(r"[a-z0-9]+", sin_acentos)
        if len(tok) >= 3 and tok not in _STOPWORDS_ES
    ]


def _seleccionar_procesos_relevantes(*, consulta, ruta_actual, catalogo, limite=4):
    """Reduce el catálogo enviado al LLM a los procesos más relevantes para acelerar la inferencia en CPU."""

    if len(catalogo) <= limite:
        return list(catalogo)

    texto_plano = _normalizar_texto_plano(consulta)
    if re.search(r"\b(pestanas|cada una|todas|secciones|opciones)\b", texto_plano):
        limite = max(limite, 6)

    tokens_consulta = _normalizar_tokens(consulta)
    ruta_norm = (ruta_actual or "/").strip().rstrip("/") or "/"

    puntuados = []
    for indice, item in enumerate(catalogo):
        score = 0
        ruta_obj = (item.get("ruta_objetivo") or "").strip().rstrip("/") or "/"
        if ruta_obj == ruta_norm or (
            ruta_obj != "/" and ruta_norm.startswith(f"{ruta_obj}/")
        ):
            score += 3

        if tokens_consulta:
            control = NOMBRES_VISUALES_UI.get(item.get("id_accion") or "", "")
            menu = NOMBRES_VISUALES_UI.get(item.get("id_menu") or "", "")
            tokens_titulo = set(_normalizar_tokens(f"{item['modulo']} {menu} {control}"))
            tokens_desc = set(
                _normalizar_tokens(f"{item['id'].replace('_', ' ')} {item['descripcion']}")
            )
            for tok in tokens_consulta:
                pref = tok[:4] if len(tok) >= 4 else tok
                if tok in tokens_titulo or any(t.startswith(pref) for t in tokens_titulo):
                    score += 4
                elif tok in tokens_desc or any(t.startswith(pref) for t in tokens_desc):
                    score += 2

        puntuados.append((score, indice, item))

    puntuados.sort(key=lambda par: (-par[0], par[1]))
    return [item for _, _, item in puntuados[:limite]]


def _parsear_contexto_ruta(ruta_actual):
    texto = (ruta_actual or "/").strip()
    if " | pestaña: " in texto:
        ruta_base, pestana = texto.split(" | pestaña: ", 1)
        return (ruta_base.strip() or "/"), pestana.strip()
    return (texto or "/"), ""


def _construir_prompt_sistema(*, roles, ruta_actual, catalogo, pestana_activa=""):
    diccionario = [
        {
            "proceso_id": item["id"],
            "modulo": item["modulo"],
            "menu": NOMBRES_VISUALES_UI.get(item["id_menu"], item["modulo"]),
            "control": NOMBRES_VISUALES_UI.get(item["id_accion"])
            if item["id_accion"]
            else None,
            "descripcion": item["descripcion"],
        }
        for item in catalogo
    ]
    ruta_norm = (ruta_actual or "/").strip().rstrip("/") or "/"
    modulo_actual = next(
        (
            item["modulo"]
            for item in catalogo
            if ((item.get("ruta_objetivo") or "").strip().rstrip("/") or "/") == ruta_norm
        ),
        None,
    )
    if modulo_actual and pestana_activa:
        ubicacion = (
            f"Usuario ya en '{modulo_actual}', pestaña activa '{pestana_activa}'. "
            f"No lo mandes al menú lateral ni digas que otra pestaña está dentro de '{pestana_activa}'."
        )
    elif modulo_actual:
        ubicacion = (
            f"Usuario ya en '{modulo_actual}'. Si pregunta sobre '{modulo_actual}', "
            f"indica el control en pantalla sin mandarlo al menú lateral."
        )
    else:
        ubicacion = f"Ruta actual: {ruta_actual}."

    return (
        "Eres el Asistente Guía de Clínicas SaaS. Responde en español de forma clara y completa (1 a 3 oraciones).\n"
        f"Roles: {', '.join(roles)}. {ubicacion}\n"
        "Reglas:\n"
        "- Usa SOLO el catálogo abajo. Si la acción no existe en el catálogo de su rol, responde en 1 oración que su rol no tiene permiso (sin sugerir otros módulos) con tipo_consulta='informacion' y proceso_id='ninguno'.\n"
        "- tipo_consulta='informacion' para qué es/para qué sirve/dudas de regla o sí-no; 'proceso' solo para cómo/dónde hacer una acción.\n"
        "- En explicacion responde directo ('Sí,...'/'No,...' en preguntas de regla) usando solo nombres visibles de menu y control.\n"
        f"Catálogo:\n{json.dumps(diccionario, ensure_ascii=False, separators=(',', ':'))}"
    )


def _consultar_ollama(*, prompt_sistema, consulta, esquema):
    payload = json.dumps(
        {
            "model": settings.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "30m",
            "format": esquema,
            "options": {"temperature": 0.0, "num_predict": 180, "num_ctx": 1536},
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": consulta},
            ],
        }
    ).encode("utf-8")

    peticion = urllib_request.Request(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(
            peticion, timeout=settings.OLLAMA_TIMEOUT_SECONDS
        ) as respuesta:
            cuerpo = json.loads(respuesta.read().decode("utf-8"))
    except (
        urllib_error.HTTPError,
        urllib_error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        raise AsistenteNoDisponible() from exc

    contenido = (cuerpo.get("message") or {}).get("content", "")
    if not contenido:
        raise AsistenteNoDisponible()

    try:
        datos = json.loads(contenido)
    except ValueError as exc:
        raise AsistenteNoDisponible() from exc

    if not isinstance(datos, dict):
        raise AsistenteNoDisponible()
    return datos


def _reemplazar_ids_por_nombres_visuales(texto):
    resultado = texto
    for guia_id, nombre_visual in sorted(
        NOMBRES_VISUALES_UI.items(), key=lambda par: len(par[0]), reverse=True
    ):
        patron = re.compile(rf"[`'\"«]?{re.escape(guia_id)}[`'\"»]?")
        resultado = patron.sub(nombre_visual, resultado)
    return resultado


def _etiquetas_citadas_control(item):
    guia_id = item.get("id_accion") or item.get("id_menu")
    if not guia_id:
        return []
    etiqueta = NOMBRES_VISUALES_UI.get(guia_id, "")
    encontradas = [c.lower() for c in re.findall(r"'([^']+)'", etiqueta)]
    return encontradas[:1]


def _posicion_etiqueta_en_texto(texto_lower, etiqueta):
    # Etiquetas cortas o verbos comunes (ej. 'ver', 'roles', 'cuenta') solo coinciden
    # si el modelo las citó explícitamente entre comillas para evitar falsos positivos.
    patron_citado = re.compile(rf"['\"«`]{re.escape(etiqueta)}['\"»`]")
    coincidencias = list(patron_citado.finditer(texto_lower))
    if coincidencias:
        return coincidencias[-1].start()
    if len(etiqueta) >= 7:
        return texto_lower.rfind(etiqueta)
    return -1


def _inferir_proceso_por_nombres_visuales(texto, catalogo):
    """Fallback determinístico usando el último control visible citado explícitamente en la respuesta."""

    texto_lower = texto.lower()
    mejor = None
    mejor_pos = -1
    for item in catalogo:
        coincidencias = _etiquetas_citadas_control(item)
        if not coincidencias:
            continue
        posiciones = [_posicion_etiqueta_en_texto(texto_lower, c) for c in coincidencias]
        if all(pos >= 0 for pos in posiciones):
            pos_max = max(posiciones)
            if pos_max > mejor_pos:
                mejor_pos = pos_max
                mejor = item
    return mejor


def _es_consulta_procedimental(consulta):
    texto = (consulta or "").lower()
    return bool(
        re.search(r"\b(c[oó]mo|d[oó]nde|pasos)\b", texto)
    )


def _es_consulta_o_respuesta_informativa(consulta, explicacion, tipo_consulta):
    if _es_consulta_procedimental(consulta):
        return False
    if tipo_consulta == "informacion":
        return True
    q = (consulta or "").strip().lower()
    if re.search(
        r"\b(para\s+qu[eé]|qu[eé]\s+es|qu[eé]\s+hace|se\s+puede|es\s+posible|puedo\s+|puede\s+un|si\s+puedo)\b",
        q,
    ):
        return True
    exp = (explicacion or "").strip().lower()
    return bool(
        re.match(r"^no[\s,.]", exp)
        or re.search(
            r"\b(no\s+se\s+puede|no\s+es\s+posible|no\s+puedes|no\s+est[aá]\s+permitido|solo\s+se\s+puede)\b",
            exp,
        )
    )


def _validar_y_sanear_respuesta(datos, catalogo, consulta=""):
    explicacion = _reemplazar_ids_por_nombres_visuales(
        str(datos.get("explicacion") or "").strip()
    )
    if not explicacion:
        raise AsistenteNoDisponible()

    pasos_crudos = datos.get("pasos")
    pasos = (
        [
            _reemplazar_ids_por_nombres_visuales(str(p).strip())
            for p in pasos_crudos
            if str(p).strip()
        ]
        if isinstance(pasos_crudos, list)
        else []
    )

    catalogo_por_id = {item["id"]: item for item in catalogo}
    proceso_id = datos.get("proceso_id")
    proceso = (
        catalogo_por_id.get(proceso_id)
        if isinstance(proceso_id, str)
        else None
    )
    texto_respuesta = f"{explicacion} {' '.join(pasos)}"
    if proceso is None:
        proceso = _inferir_proceso_por_nombres_visuales(texto_respuesta, catalogo)
    else:
        # Si el modelo eligió un proceso cuyo control NO aparece citado en su propia
        # explicación, pero sí citó explícitamente el control de otro proceso autorizado
        # (del mismo u otro módulo), alinear el resaltado y los pasos con el control citado.
        explicacion_lower = explicacion.lower()
        etiquetas_actuales = _etiquetas_citadas_control(proceso)
        cita_su_propio_control = bool(etiquetas_actuales) and all(
            e in explicacion_lower for e in etiquetas_actuales
        )
        if not cita_su_propio_control:
            modulo_actual_citado = proceso["modulo"].lower() in explicacion_lower
            candidatos = (
                [
                    item
                    for item in catalogo
                    if item.get("ruta_objetivo") == proceso.get("ruta_objetivo")
                ]
                if modulo_actual_citado
                else catalogo
            )
            inferido = _inferir_proceso_por_nombres_visuales(explicacion, candidatos)
            if inferido and inferido["id"] != proceso["id"]:
                proceso = inferido

    # Si el modelo indicó rechazo de permiso en su primera oración, conservar solo esa
    # oración y limpiar cualquier resaltado/paso aunque haya elegido un proceso_id por error.
    primera_oracion = explicacion.split(".", 1)[0].strip()
    if re.search(
        r"\b(no\s+tiene[sn]?\s+permiso|no\s+tiene[sn]?\s+acceso|no\s+est[aá]\s+permitid[oa]|no\s+cuenta\s+con\s+permiso)\b",
        primera_oracion.lower(),
    ):
        return {
            "explicacion": f"{primera_oracion}.",
            "pasos": [],
            "id_accion": None,
            "id_menu": None,
            "ruta_objetivo": None,
        }

    tipo_consulta = datos.get("tipo_consulta")
    es_informativa = _es_consulta_o_respuesta_informativa(
        consulta, explicacion, tipo_consulta
    )

    # Si el modelo devolvió una explicación demasiado corta (ej. solo el nombre del módulo),
    # usar la descripción completa del catálogo para responder con claridad.
    if proceso and (
        len(explicacion) < 30
        or explicacion.rstrip(".").lower() == proceso["modulo"].lower()
    ):
        explicacion = proceso["descripcion"]

    id_accion = (
        None
        if (es_informativa and proceso and proceso["id_menu"] is not None)
        else (proceso["id_accion"] if proceso else None)
    )
    id_menu = proceso["id_menu"] if proceso else None
    ruta_objetivo = proceso["ruta_objetivo"] if proceso else None

    # Si el modelo dejó pasos vacíos (en consultas de proceso) o con claves técnicas,
    # usar pasos_base del proceso (o limpiar pasos si era informativa con tokens técnicos).
    tokens_tecnicos = (
        "proceso_id",
        "id_accion",
        "id_menu",
        "ruta_objetivo",
        "nombre_menu",
        "nombre_accion",
    )
    pasos_son_tecnicos = any(
        any(tok in paso for tok in tokens_tecnicos)
        or (proceso and proceso["id"] in paso)
        for paso in pasos
    )
    if es_informativa:
        pasos = []
    elif (not pasos or pasos_son_tecnicos) and proceso and proceso.get("pasos_base"):
        pasos = list(proceso["pasos_base"])

    return {
        "explicacion": explicacion,
        "pasos": pasos,
        "id_accion": id_accion,
        "id_menu": id_menu,
        "ruta_objetivo": ruta_objetivo,
    }


def consultar_asistente_guia(*, usuario, consulta, ruta_actual="/"):
    roles = obtener_roles_activos_usuario(usuario)
    if not roles:
        raise PermisoDenegado(
            "El usuario no tiene un rol activo asignado en la clínica.",
            codigo="rol_requerido",
        )

    accion_denegada = _verificar_permiso_consulta(consulta, roles)
    if accion_denegada:
        return {
            "explicacion": f"No tienes el permiso necesario con tu rol actual para {accion_denegada}.",
            "pasos": [],
            "id_accion": None,
            "id_menu": None,
            "ruta_objetivo": None,
        }

    ruta_limpia, pestana_activa = _parsear_contexto_ruta(ruta_actual)
    clave_cache = (
        tuple(sorted(roles)),
        ruta_limpia,
        pestana_activa,
        _normalizar_texto_plano(consulta),
    )
    ahora = time.monotonic()
    entrada_cache = _CACHE_RESPUESTAS.get(clave_cache)
    if entrada_cache and (ahora - entrada_cache[0]) < _CACHE_TTL_SEGUNDOS:
        return dict(entrada_cache[1])

    catalogo_completo = filtrar_catalogo_por_roles(roles, ruta_actual=ruta_limpia)
    catalogo = _seleccionar_procesos_relevantes(
        consulta=consulta,
        ruta_actual=ruta_limpia,
        catalogo=catalogo_completo,
    )
    prompt_sistema = _construir_prompt_sistema(
        roles=roles,
        ruta_actual=ruta_limpia,
        catalogo=catalogo,
        pestana_activa=pestana_activa,
    )
    esquema = _construir_esquema_ollama(catalogo)
    datos = _consultar_ollama(
        prompt_sistema=prompt_sistema,
        consulta=consulta,
        esquema=esquema,
    )
    resultado = _validar_y_sanear_respuesta(datos, catalogo_completo, consulta=consulta)

    if len(_CACHE_RESPUESTAS) >= _CACHE_MAX_ENTRADAS:
        _CACHE_RESPUESTAS.clear()
    _CACHE_RESPUESTAS[clave_cache] = (ahora, dict(resultado))
    return resultado
