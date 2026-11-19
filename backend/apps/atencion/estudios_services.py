"""Servicios de negocio e integración con Supabase Storage para estudios médicos."""

import os
from urllib import error as urllib_error, parse as urllib_parse, request as urllib_request
import uuid

from django.conf import settings
from django.db import transaction

from apps.core.api_exceptions import Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.core.permissions import tiene_rol
from apps.core.seed_data import ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE
from apps.pacientes.models import HistoriaClinica, Paciente

from .models import (
    Cita,
    Consulta,
    EstadoCita,
    EstadoEstudio,
    EstudioMedico,
    FormatoEstudio,
)
from .portal_paciente_services import obtener_paciente_autenticado
from .services import obtener_medico_usuario


MAX_TAMANO_BYTES = 50 * 1024 * 1024  # 50 MB

EXTENSIONES_FORMATO = {
    ".dcm": (FormatoEstudio.DICOM, "application/dicom"),
    ".png": (FormatoEstudio.IMAGEN, "image/png"),
    ".jpg": (FormatoEstudio.IMAGEN, "image/jpeg"),
    ".jpeg": (FormatoEstudio.IMAGEN, "image/jpeg"),
    ".pdf": (FormatoEstudio.PDF, "application/pdf"),
}

ESTADOS_CITA_CERRADA = (
    EstadoCita.ATENDIDA,
    EstadoCita.CANCELADA,
    EstadoCita.NO_ASISTIO,
)


def _validar_config_supabase():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise Conflicto(
            "Falta configurar SUPABASE_URL o SUPABASE_SECRET_KEY en el servidor.",
            codigo="storage_no_configurado",
        )


def _headers_supabase(content_type=None, extra=None):
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
        "apikey": settings.SUPABASE_SECRET_KEY,
    }
    if content_type:
        headers["Content-Type"] = content_type
    if extra:
        headers.update(extra)
    return headers


def _url_objeto_supabase(ruta_storage, *, publico=False):
    bucket = urllib_parse.quote(settings.SUPABASE_STORAGE_BUCKET, safe="")
    ruta = urllib_parse.quote(ruta_storage.lstrip("/"), safe="/")
    prefijo = "public/" if publico else ""
    return f"{settings.SUPABASE_URL}/storage/v1/object/{prefijo}{bucket}/{ruta}"


def _subir_a_supabase(ruta_storage, contenido, content_type):
    _validar_config_supabase()
    peticion = urllib_request.Request(
        _url_objeto_supabase(ruta_storage, publico=False),
        data=contenido,
        headers=_headers_supabase(content_type=content_type, extra={"x-upsert": "true"}),
        method="POST",
    )
    try:
        with urllib_request.urlopen(peticion, timeout=30) as respuesta:
            respuesta.read()
    except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError) as exc:
        raise Conflicto(
            "No se pudo subir el archivo del estudio médico a Supabase Storage.",
            codigo="error_storage",
        ) from exc
    return _url_objeto_supabase(ruta_storage, publico=True)


def _descargar_de_supabase(ruta_storage):
    _validar_config_supabase()
    peticion = urllib_request.Request(
        _url_objeto_supabase(ruta_storage, publico=False),
        headers=_headers_supabase(),
        method="GET",
    )
    try:
        with urllib_request.urlopen(peticion, timeout=30) as respuesta:
            contenido = respuesta.read()
            content_type = respuesta.headers.get("Content-Type") or "application/octet-stream"
            return contenido, content_type
    except urllib_error.HTTPError as exc:
        if exc.code == 404:
            raise RecursoNoEncontrado(
                "Archivo de estudio no encontrado en almacenamiento.",
                codigo="no_encontrado",
            ) from exc
        raise Conflicto(
            "No se pudo descargar el archivo desde Supabase Storage.",
            codigo="error_storage",
        ) from exc
    except (urllib_error.URLError, TimeoutError) as exc:
        raise Conflicto(
            "No se pudo descargar el archivo desde Supabase Storage.",
            codigo="error_storage",
        ) from exc


def _eliminar_de_supabase(ruta_storage):
    if not ruta_storage or not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        return
    peticion = urllib_request.Request(
        _url_objeto_supabase(ruta_storage, publico=False),
        headers=_headers_supabase(),
        method="DELETE",
    )
    try:
        with urllib_request.urlopen(peticion, timeout=15) as respuesta:
            respuesta.read()
    except urllib_error.HTTPError as exc:
        if exc.code != 404:
            raise Conflicto(
                "No se pudo eliminar el archivo de Supabase Storage.",
                codigo="error_storage",
            ) from exc
    except (urllib_error.URLError, TimeoutError) as exc:
        raise Conflicto(
            "No se pudo eliminar el archivo de Supabase Storage.",
            codigo="error_storage",
        ) from exc


def _validar_archivo(archivo):
    if archivo is None:
        raise DatosInvalidos(
            "Debe adjuntar un archivo.",
            codigo="datos_invalidos",
            detalles={"archivo": ["El archivo es obligatorio."]},
        )
    if archivo.size > MAX_TAMANO_BYTES:
        raise DatosInvalidos(
            "El archivo supera el tamaño máximo permitido de 50 MB.",
            codigo="archivo_demasiado_grande",
            detalles={"archivo": ["Tamaño máximo permitido: 50 MB."]},
        )
    nombre_limpio = os.path.basename(archivo.name or "").strip()
    if not nombre_limpio:
        raise DatosInvalidos(
            "Nombre de archivo inválido.",
            codigo="datos_invalidos",
            detalles={"archivo": ["El nombre del archivo no es válido."]},
        )
    _, ext = os.path.splitext(nombre_limpio.lower())
    if ext not in EXTENSIONES_FORMATO:
        raise DatosInvalidos(
            "Formato de archivo no soportado. Use .dcm, .png, .jpg, .jpeg o .pdf.",
            codigo="formato_no_soportado",
            detalles={"archivo": ["Formatos permitidos: .dcm, .png, .jpg, .jpeg, .pdf."]},
        )
    formato, content_type = EXTENSIONES_FORMATO[ext]
    return nombre_limpio[:255], formato, content_type, ext


def cita_cerrada_para_estudios(cita):
    if cita is None:
        return False
    if cita.estado in ESTADOS_CITA_CERRADA:
        return True
    return Consulta.all_objects.filter(cita=cita).exists()


def _validar_cita_abierta(cita):
    if cita_cerrada_para_estudios(cita):
        raise Conflicto(
            "No se pueden subir ni modificar estudios porque la cita ya tiene una consulta registrada o está finalizada.",
            codigo="cita_cerrada_estudios",
        )


def _queryset_estudios_para_usuario(*, usuario, clinica):
    queryset = EstudioMedico.all_objects.filter(clinica=clinica).select_related(
        "paciente",
        "historia_clinica",
        "cita",
        "consulta",
        "medico__personal",
    )
    if tiene_rol(usuario, ROL_ADMIN_CLINICA):
        return queryset
    if tiene_rol(usuario, ROL_MEDICO):
        obtener_medico_usuario(usuario=usuario, clinica=clinica)
        return queryset
    if tiene_rol(usuario, ROL_PACIENTE):
        paciente = obtener_paciente_autenticado(usuario=usuario, clinica=clinica)
        return queryset.filter(paciente=paciente)
    return queryset.none()


def listar_estudios(*, usuario, clinica, filtros):
    queryset = _queryset_estudios_para_usuario(usuario=usuario, clinica=clinica)
    if filtros.get("cita_id"):
        queryset = queryset.filter(cita_id=filtros["cita_id"])
    if filtros.get("paciente_id"):
        queryset = queryset.filter(paciente_id=filtros["paciente_id"])
    if filtros.get("consulta_id"):
        queryset = queryset.filter(consulta_id=filtros["consulta_id"])
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("formato"):
        queryset = queryset.filter(formato=filtros["formato"])
    return queryset.order_by("-fecha_estudio", "-id")


def obtener_estudio(*, usuario, clinica, estudio_id):
    estudio = _queryset_estudios_para_usuario(usuario=usuario, clinica=clinica).filter(
        pk=estudio_id
    ).first()
    if estudio is None:
        raise RecursoNoEncontrado("Estudio médico no encontrado.", codigo="no_encontrado")
    return estudio


def _resolver_paciente_y_cita_para_subida(*, usuario, clinica, cita_id, paciente_id):
    es_paciente = tiene_rol(usuario, ROL_PACIENTE) and not (
        tiene_rol(usuario, ROL_MEDICO) or tiene_rol(usuario, ROL_ADMIN_CLINICA)
    )

    if es_paciente:
        paciente = obtener_paciente_autenticado(usuario=usuario, clinica=clinica)
        cita = None
        if cita_id is not None:
            cita = Cita.all_objects.filter(
                pk=cita_id, clinica=clinica, paciente=paciente
            ).first()
            if cita is None:
                raise RecursoNoEncontrado("Cita no encontrada.", codigo="no_encontrado")
        return paciente, cita

    cita = None
    if cita_id is not None:
        cita = Cita.all_objects.select_related("paciente").filter(
            pk=cita_id, clinica=clinica
        ).first()
        if cita is None:
            raise RecursoNoEncontrado("Cita no encontrada.", codigo="no_encontrado")
        paciente = cita.paciente
        if paciente_id is not None and paciente.pk != paciente_id:
            raise DatosInvalidos(
                "El paciente no coincide con el de la cita.",
                codigo="datos_invalidos",
            )
        return paciente, cita

    if paciente_id is None:
        raise DatosInvalidos(
            "Debe indicar cita_id o paciente_id.",
            codigo="datos_invalidos",
            detalles={"paciente_id": ["Indique el paciente o la cita asociada."]},
        )
    paciente = Paciente.all_objects.filter(pk=paciente_id, clinica=clinica).first()
    if paciente is None:
        raise RecursoNoEncontrado("Paciente no encontrado.", codigo="no_encontrado")
    return paciente, None


def crear_estudio(*, usuario, clinica, datos):
    archivo = datos["archivo"]
    nombre_archivo, formato, content_type, ext = _validar_archivo(archivo)

    paciente, cita = _resolver_paciente_y_cita_para_subida(
        usuario=usuario,
        clinica=clinica,
        cita_id=datos.get("cita_id"),
        paciente_id=datos.get("paciente_id"),
    )
    if not paciente.estado:
        raise Conflicto("El paciente está inactivo.", codigo="paciente_inactivo")
    _validar_cita_abierta(cita)

    historia = HistoriaClinica.all_objects.filter(
        paciente=paciente, paciente__clinica=clinica
    ).first()

    ruta_storage = f"clinicas/{clinica.pk}/pacientes/{paciente.pk}/{uuid.uuid4().hex}{ext}"
    contenido = archivo.read()
    url_archivo = _subir_a_supabase(ruta_storage, contenido, content_type)

    try:
        with transaction.atomic():
            return EstudioMedico.all_objects.create(
                clinica=clinica,
                paciente=paciente,
                historia_clinica=historia,
                cita=cita,
                tipo_estudio=datos["tipo_estudio"],
                formato=formato,
                nombre_archivo=nombre_archivo,
                url_archivo=url_archivo,
                ruta_storage=ruta_storage,
                estado=EstadoEstudio.PENDIENTE_REVISION,
            )
    except Exception:
        try:
            _eliminar_de_supabase(ruta_storage)
        except Exception:
            pass
        raise


def actualizar_estudio(*, usuario, clinica, estudio_id, datos):
    estudio = obtener_estudio(usuario=usuario, clinica=clinica, estudio_id=estudio_id)
    _validar_cita_abierta(estudio.cita)
    if estudio.consulta_id is not None:
        raise Conflicto(
            "No se puede modificar un estudio ya asociado a una consulta.",
            codigo="cita_cerrada_estudios",
        )

    campos = []
    if "tipo_estudio" in datos:
        estudio.tipo_estudio = datos["tipo_estudio"]
        campos.append("tipo_estudio")

    ruta_anterior = None
    nueva_ruta = None
    if datos.get("archivo") is not None:
        archivo = datos["archivo"]
        nombre_archivo, formato, content_type, ext = _validar_archivo(archivo)
        nueva_ruta = f"clinicas/{clinica.pk}/pacientes/{estudio.paciente_id}/{uuid.uuid4().hex}{ext}"
        url_archivo = _subir_a_supabase(nueva_ruta, archivo.read(), content_type)
        ruta_anterior = estudio.ruta_storage
        estudio.nombre_archivo = nombre_archivo
        estudio.formato = formato
        estudio.url_archivo = url_archivo
        estudio.ruta_storage = nueva_ruta
        campos.extend(["nombre_archivo", "formato", "url_archivo", "ruta_storage"])

    if campos:
        with transaction.atomic():
            estudio.save(update_fields=campos)
        if ruta_anterior and ruta_anterior != nueva_ruta:
            try:
                _eliminar_de_supabase(ruta_anterior)
            except Exception:
                pass

    return estudio


def eliminar_estudio(*, usuario, clinica, estudio_id):
    estudio = obtener_estudio(usuario=usuario, clinica=clinica, estudio_id=estudio_id)
    _validar_cita_abierta(estudio.cita)
    if estudio.consulta_id is not None:
        raise Conflicto(
            "No se puede eliminar un estudio ya asociado a una consulta.",
            codigo="cita_cerrada_estudios",
        )
    ruta_storage = estudio.ruta_storage
    with transaction.atomic():
        estudio.delete()
    if ruta_storage:
        _eliminar_de_supabase(ruta_storage)


def revisar_estudio(*, usuario, clinica, estudio_id, datos):
    _, medico = obtener_medico_usuario(usuario=usuario, clinica=clinica)
    estudio = obtener_estudio(usuario=usuario, clinica=clinica, estudio_id=estudio_id)

    consulta = estudio.consulta
    consulta_id = datos.get("consulta_id")
    if consulta_id is not None:
        consulta = Consulta.all_objects.filter(
            pk=consulta_id,
            clinica=clinica,
            paciente_id=estudio.paciente_id,
        ).first()
        if consulta is None:
            raise RecursoNoEncontrado("Consulta no encontrada.", codigo="no_encontrado")
    elif consulta is None and estudio.cita_id is not None:
        consulta = Consulta.all_objects.filter(
            cita_id=estudio.cita_id, clinica=clinica
        ).first()

    estudio.medico = medico
    estudio.consulta = consulta
    estudio.observacion_lectura = datos.get("observacion_lectura", "")
    estudio.estado = EstadoEstudio.REVISADO
    estudio.save(update_fields=["medico", "consulta", "observacion_lectura", "estado"])
    return estudio


def descargar_archivo_estudio(*, usuario, clinica, estudio_id):
    estudio = obtener_estudio(usuario=usuario, clinica=clinica, estudio_id=estudio_id)
    if not estudio.ruta_storage:
        raise RecursoNoEncontrado(
            "El estudio no tiene un archivo en almacenamiento.",
            codigo="no_encontrado",
        )
    contenido, content_type = _descargar_de_supabase(estudio.ruta_storage)
    _, ext = os.path.splitext(estudio.nombre_archivo.lower())
    if ext in EXTENSIONES_FORMATO:
        content_type = EXTENSIONES_FORMATO[ext][1]
    return estudio, contenido, content_type
