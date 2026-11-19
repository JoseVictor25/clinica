"""Reglas de negocio para la creación y disponibilidad de citas."""

from datetime import datetime, timedelta
import json
import unicodedata
from urllib import error as urllib_error, request as urllib_request
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.core.api_exceptions import Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.core.permissions import tiene_rol
from apps.core.seed_data import ROL_MEDICO
from apps.pacientes.models import Alergia, HistoriaClinica, Paciente, TipoAlergia
from apps.personal.models import DiaSemana, HorarioAtencion, Medico, Personal

from .models import (
    Cita,
    Consulta,
    EstadoCita,
    EstudioMedico,
    MedicamentoRecetado,
    ModalidadCita,
    Receta,
)


DURACION_CITA_MINUTOS = 30
ESTADOS_QUE_NO_BLOQUEAN = (
    EstadoCita.CANCELADA,
    EstadoCita.NO_ASISTIO,
)
DIA_SEMANA_DESDE_WEEKDAY = {
    0: DiaSemana.LUNES,
    1: DiaSemana.MARTES,
    2: DiaSemana.MIERCOLES,
    3: DiaSemana.JUEVES,
    4: DiaSemana.VIERNES,
    5: DiaSemana.SABADO,
    6: DiaSemana.DOMINGO,
}


def _momento_local():
    """Devuelve el instante actual en la zona horaria configurada."""

    return timezone.localtime()


def _instante_local(fecha, hora):
    return timezone.make_aware(
        datetime.combine(fecha, hora),
        timezone.get_current_timezone(),
    )


def _intervalo(fecha, hora):
    inicio = datetime.combine(fecha, hora)
    return inicio, inicio + timedelta(minutes=DURACION_CITA_MINUTOS)


def _se_solapan(inicio_a, fin_a, inicio_b, fin_b):
    """Compara intervalos semiabiertos: [inicio, fin)."""

    return inicio_a < fin_b and inicio_b < fin_a


def _validar_fecha(fecha, ahora=None):
    ahora = ahora or _momento_local()
    if fecha < ahora.date():
        raise DatosInvalidos(
            "No se puede crear una cita en una fecha pasada.",
            codigo="fecha_cita_pasada",
            detalles={"fecha": ["La fecha de la cita ya pasó."]},
        )


def _validar_momento(fecha, hora, ahora=None):
    ahora = ahora or _momento_local()
    _validar_fecha(fecha, ahora)
    if _instante_local(fecha, hora) < ahora:
        raise DatosInvalidos(
            "No se puede crear una cita en una hora pasada.",
            codigo="hora_cita_pasada",
            detalles={"hora": ["La hora de la cita ya pasó."]},
        )


def obtener_paciente_cita(*, clinica, paciente_id, bloquear=False):
    queryset = Paciente.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=paciente_id, clinica=clinica)
    except Paciente.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Paciente no encontrado.", codigo="no_encontrado"
        ) from exc


def obtener_medico_cita(*, clinica, medico_id, bloquear=False):
    queryset = Medico.all_objects.select_related("especialidad")
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=medico_id, clinica=clinica)
    except Medico.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Médico no encontrado.", codigo="no_encontrado"
        ) from exc


def _obtener_personal_medico(*, clinica, medico, bloquear=False):
    queryset = Personal.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=medico.personal_id, clinica=clinica)
    except Personal.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Personal del médico no encontrado.",
            codigo="no_encontrado",
        ) from exc


def _validar_recursos_activos(*, paciente, medico, personal):
    if not paciente.estado:
        raise Conflicto(
            "El paciente está inactivo.", codigo="paciente_inactivo"
        )
    if not medico.estado or not personal.estado:
        raise Conflicto("El médico está inactivo.", codigo="medico_inactivo")


def generar_bloques_horario(*, clinica, medico, fecha):
    """Genera inicios de bloques completos de 30 minutos del médico."""

    dia_semana = DIA_SEMANA_DESDE_WEEKDAY[fecha.weekday()]
    horarios = HorarioAtencion.all_objects.filter(
        medico=medico,
        medico__clinica=clinica,
        dia_semana=dia_semana,
    ).order_by("hora_inicio")

    bloques = set()
    duracion = timedelta(minutes=DURACION_CITA_MINUTOS)
    for horario in horarios:
        cursor = datetime.combine(fecha, horario.hora_inicio)
        fin_horario = datetime.combine(fecha, horario.hora_fin)
        while cursor + duracion <= fin_horario:
            bloques.add(cursor.time())
            cursor += duracion
    return sorted(bloques)


def _validar_bloque_horario(*, clinica, medico, fecha, hora):
    if hora not in generar_bloques_horario(
        clinica=clinica, medico=medico, fecha=fecha
    ):
        raise DatosInvalidos(
            "La hora elegida está fuera del horario de atención del médico.",
            codigo="fuera_horario",
            detalles={
                "hora": [
                    "Seleccione un bloque disponible de 30 minutos dentro del horario del médico."
                ]
            },
        )


def _citas_que_bloquean(
    *,
    clinica,
    fecha,
    medico=None,
    paciente=None,
    excluir_cita_id=None,
):
    queryset = Cita.all_objects.filter(
        clinica=clinica,
        fecha=fecha,
    ).exclude(estado__in=ESTADOS_QUE_NO_BLOQUEAN)
    if medico is not None:
        queryset = queryset.filter(medico=medico)
    if paciente is not None:
        queryset = queryset.filter(paciente=paciente)
    if excluir_cita_id is not None:
        queryset = queryset.exclude(pk=excluir_cita_id)
    return queryset


def _hay_solapamiento(queryset, *, fecha, hora):
    inicio_nuevo, fin_nuevo = _intervalo(fecha, hora)
    for hora_existente in queryset.values_list("hora", flat=True):
        inicio_existente, fin_existente = _intervalo(fecha, hora_existente)
        if _se_solapan(
            inicio_nuevo, fin_nuevo, inicio_existente, fin_existente
        ):
            return True
    return False


def _validar_disponibilidad(
    *,
    clinica,
    paciente,
    medico,
    fecha,
    hora,
    excluir_cita_id=None,
):
    if _hay_solapamiento(
        _citas_que_bloquean(
            clinica=clinica,
            fecha=fecha,
            medico=medico,
            excluir_cita_id=excluir_cita_id,
        ),
        fecha=fecha,
        hora=hora,
    ):
        raise Conflicto(
            "El horario seleccionado ya no está disponible para el médico.",
            codigo="horario_no_disponible",
        )

    if _hay_solapamiento(
        _citas_que_bloquean(
            clinica=clinica,
            fecha=fecha,
            paciente=paciente,
            excluir_cita_id=excluir_cita_id,
        ),
        fecha=fecha,
        hora=hora,
    ):
        raise Conflicto(
            "El paciente ya tiene una cita que se solapa con este horario.",
            codigo="paciente_no_disponible",
        )


def _obtener_cita_tenant(*, clinica, cita_id, bloquear=False):
    queryset = Cita.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=cita_id, clinica=clinica)
    except Cita.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Cita no encontrada.", codigo="no_encontrado"
        ) from exc


def _validar_cita_para_exclusion(*, cita, paciente, medico):
    if cita.paciente_id != paciente.pk or cita.medico_id != medico.pk:
        raise DatosInvalidos(
            "La cita no corresponde al paciente y médico indicados.",
            detalles={
                "cita_id": [
                    "La cita debe pertenecer al paciente y médico seleccionados."
                ]
            },
        )
    if cita.estado not in (EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA):
        raise Conflicto(
            "La cita no puede reprogramarse en su estado actual.",
            codigo="cita_no_reprogramable",
        )


def obtener_disponibilidad(
    clinica,
    paciente_id,
    medico_id,
    fecha,
    cita_id=None,
):
    """Devuelve los bloques futuros libres de un médico activo."""

    ahora = _momento_local()
    paciente = obtener_paciente_cita(
        clinica=clinica, paciente_id=paciente_id, bloquear=False
    )
    medico = obtener_medico_cita(
        clinica=clinica, medico_id=medico_id, bloquear=False
    )
    personal = _obtener_personal_medico(
        clinica=clinica, medico=medico, bloquear=False
    )
    _validar_recursos_activos(
        paciente=paciente, medico=medico, personal=personal
    )
    _validar_fecha(fecha, ahora)

    if cita_id is not None:
        cita = _obtener_cita_tenant(
            clinica=clinica,
            cita_id=cita_id,
            bloquear=False,
        )
        _validar_cita_para_exclusion(
            cita=cita,
            paciente=paciente,
            medico=medico,
        )

    citas_medico = _citas_que_bloquean(
        clinica=clinica,
        fecha=fecha,
        medico=medico,
        excluir_cita_id=cita_id,
    )
    citas_paciente = _citas_que_bloquean(
        clinica=clinica,
        fecha=fecha,
        paciente=paciente,
        excluir_cita_id=cita_id,
    )
    disponibles = []
    for hora in generar_bloques_horario(
        clinica=clinica, medico=medico, fecha=fecha
    ):
        if _instante_local(fecha, hora) < ahora:
            continue
        if not _hay_solapamiento(citas_medico, fecha=fecha, hora=hora) and not _hay_solapamiento(
            citas_paciente, fecha=fecha, hora=hora
        ):
            disponibles.append(hora)
    return {
        "paciente_id": paciente.pk,
        "medico_id": medico.pk,
        "fecha": fecha,
        "duracion_minutos": DURACION_CITA_MINUTOS,
        "horarios": [hora.strftime("%H:%M") for hora in disponibles],
    }


def _traducir_integrity_error(error):
    nombre_restriccion = getattr(
        getattr(error, "__cause__", None), "diag", None
    )
    nombre_restriccion = getattr(nombre_restriccion, "constraint_name", "")
    if nombre_restriccion == "uniq_cita_paciente_activa":
        return Conflicto(
            "El paciente ya tiene una cita en ese horario.",
            codigo="paciente_no_disponible",
        )
    if nombre_restriccion == "uniq_cita_medico_activa":
        return Conflicto(
            "El horario seleccionado ya no está disponible para el médico.",
            codigo="horario_no_disponible",
        )
    return None


def _generar_link_videollamada(clinica):
    """Crea una sala en Daily.co y devuelve su URL pública."""

    if not settings.DAILY_API_KEY:
        raise Conflicto(
            "Falta configurar DAILY_API_KEY en el servidor para crear salas virtuales.",
            codigo="telemedicina_no_configurada",
        )

    nombre_sala = f"clinica-{clinica.pk}-{uuid.uuid4().hex[:12]}"
    payload = json.dumps(
        {
            "name": nombre_sala,
            "privacy": "public",
            "properties": {
                "enable_chat": True,
                "enable_screenshare": True,
                "enable_prejoin_ui": False,
                "start_video_off": False,
                "start_audio_off": False,
                "lang": "es",
            },
        }
    ).encode("utf-8")

    peticion = urllib_request.Request(
        f"{settings.DAILY_API_BASE_URL}/rooms",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.DAILY_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(peticion, timeout=10) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, ValueError) as exc:
        raise Conflicto(
            "No se pudo crear la sala de videollamada en Daily.co.",
            codigo="error_daily",
        ) from exc

    url_sala = datos.get("url")
    if not url_sala:
        raise Conflicto(
            "Daily.co no devolvió una URL válida para la sala.",
            codigo="error_daily",
        )
    return url_sala


def crear_cita(clinica, datos):
    """Crea una cita después de revalidar sus reglas dentro de un bloqueo."""

    paciente_id = datos["paciente_id"]
    medico_id = datos["medico_id"]
    fecha = datos["fecha"]
    hora = datos["hora"]
    modalidad = datos.get("modalidad", ModalidadCita.PRESENCIAL)
    motivo = datos["motivo"]
    link_videollamada = (
        _generar_link_videollamada(clinica)
        if modalidad == ModalidadCita.VIRTUAL
        else None
    )

    with transaction.atomic():
        # Orden estable para reducir interbloqueos: paciente -> médico -> personal.
        paciente = obtener_paciente_cita(
            clinica=clinica, paciente_id=paciente_id, bloquear=True
        )
        medico = obtener_medico_cita(
            clinica=clinica, medico_id=medico_id, bloquear=True
        )
        personal = _obtener_personal_medico(
            clinica=clinica, medico=medico, bloquear=True
        )

        _validar_recursos_activos(
            paciente=paciente, medico=medico, personal=personal
        )
        _validar_momento(fecha, hora)
        _validar_bloque_horario(
            clinica=clinica, medico=medico, fecha=fecha, hora=hora
        )
        _validar_disponibilidad(
            clinica=clinica,
            paciente=paciente,
            medico=medico,
            fecha=fecha,
            hora=hora,
        )

        try:
            with transaction.atomic():
                return Cita.all_objects.create(
                    clinica=clinica,
                    paciente=paciente,
                    medico=medico,
                    fecha=fecha,
                    hora=hora,
                    modalidad=modalidad,
                    link_videollamada=link_videollamada,
                    motivo=motivo,
                    estado=EstadoCita.PROGRAMADA,
                )
        except IntegrityError as error:
            conflicto = _traducir_integrity_error(error)
            if conflicto is None:
                raise
            raise conflicto from error


def _cambiar_estado_cita(*, clinica, cita_id, estados_permitidos, nuevo_estado):
    with transaction.atomic():
        cita = _obtener_cita_tenant(
            clinica=clinica,
            cita_id=cita_id,
            bloquear=True,
        )
        if cita.estado not in estados_permitidos:
            raise Conflicto(
                "La transición solicitada no está permitida para el estado actual.",
                codigo="transicion_cita_invalida",
            )
        cita.estado = nuevo_estado
        cita.save(update_fields=["estado"])
        return cita


def confirmar_cita(*, clinica, cita_id):
    return _cambiar_estado_cita(
        clinica=clinica,
        cita_id=cita_id,
        estados_permitidos=(EstadoCita.PROGRAMADA,),
        nuevo_estado=EstadoCita.CONFIRMADA,
    )


def cancelar_cita(*, clinica, cita_id):
    return _cambiar_estado_cita(
        clinica=clinica,
        cita_id=cita_id,
        estados_permitidos=(EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA),
        nuevo_estado=EstadoCita.CANCELADA,
    )


def reprogramar_cita(*, clinica, cita_id, fecha, hora):
    """Reprograma con el mismo orden global de bloqueos de la creación."""

    cita_inicial = _obtener_cita_tenant(
        clinica=clinica,
        cita_id=cita_id,
        bloquear=False,
    )
    paciente_id = cita_inicial.paciente_id
    medico_id = cita_inicial.medico_id
    personal_id = cita_inicial.medico.personal_id

    with transaction.atomic():
        paciente = obtener_paciente_cita(
            clinica=clinica,
            paciente_id=paciente_id,
            bloquear=True,
        )
        medico = obtener_medico_cita(
            clinica=clinica,
            medico_id=medico_id,
            bloquear=True,
        )
        personal = _obtener_personal_medico(
            clinica=clinica,
            medico=medico,
            bloquear=True,
        )
        cita = _obtener_cita_tenant(
            clinica=clinica,
            cita_id=cita_id,
            bloquear=True,
        )

        if (
            cita.paciente_id != paciente_id
            or cita.medico_id != medico_id
            or personal.pk != personal_id
        ):
            raise Conflicto(
                "La cita cambió durante la operación. Intente nuevamente.",
                codigo="cita_no_reprogramable",
            )
        if cita.estado not in (EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA):
            raise Conflicto(
                "La cita no puede reprogramarse en su estado actual.",
                codigo="cita_no_reprogramable",
            )
        if cita.fecha == fecha and cita.hora == hora:
            raise Conflicto(
                "La nueva fecha y hora deben ser diferentes.",
                codigo="cita_no_reprogramable",
            )

        _validar_recursos_activos(
            paciente=paciente,
            medico=medico,
            personal=personal,
        )
        _validar_momento(fecha, hora)
        _validar_bloque_horario(
            clinica=clinica,
            medico=medico,
            fecha=fecha,
            hora=hora,
        )
        _validar_disponibilidad(
            clinica=clinica,
            paciente=paciente,
            medico=medico,
            fecha=fecha,
            hora=hora,
            excluir_cita_id=cita.pk,
        )

        cita.fecha = fecha
        cita.hora = hora
        cita.estado = EstadoCita.PROGRAMADA
        try:
            with transaction.atomic():
                cita.save(update_fields=["fecha", "hora", "estado"])
        except IntegrityError as error:
            conflicto = _traducir_integrity_error(error)
            if conflicto is None:
                raise
            raise conflicto from error
        return cita


def obtener_medico_usuario(*, usuario, clinica):
    """Resuelve el contexto médico activo del usuario dentro del tenant."""
    personal = Personal.all_objects.filter(
        clinica=clinica,
        usuario=usuario,
    ).first()
    if personal is None:
        raise Conflicto(
            "El usuario no tiene un registro de médico vinculado.",
            codigo="medico_no_vinculado",
        )

    medico = Medico.all_objects.filter(
        clinica=clinica,
        personal=personal,
    ).first()
    if medico is None:
        raise Conflicto(
            "El usuario no tiene un registro de médico vinculado.",
            codigo="medico_no_vinculado",
        )
    if not personal.estado or not medico.estado:
        raise Conflicto(
            "El médico está inactivo.",
            codigo="medico_inactivo",
        )
    return personal, medico


def obtener_agenda_medico(*, usuario, clinica, fecha, estado=None, ordering=None):
    """Devuelve únicamente la agenda del médico vinculado al usuario."""

    _, medico = obtener_medico_usuario(usuario=usuario, clinica=clinica)

    campos_orden = list(ordering or ("fecha", "hora", "id"))
    campos_presentes = {campo.lstrip("-") for campo in campos_orden}
    for campo in ("fecha", "hora", "id"):
        if campo not in campos_presentes:
            campos_orden.append(campo)

    queryset = Cita.all_objects.filter(
        clinica=clinica,
        medico=medico,
        fecha=fecha,
    )
    if estado:
        queryset = queryset.filter(estado=estado)
    return queryset.select_related(
        "paciente",
        "medico__personal",
        "medico__especialidad",
        "consulta",
    ).order_by(*campos_orden)


def _obtener_cita_del_medico(*, clinica, medico, cita_id, bloquear=False):
    queryset = Cita.all_objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=cita_id, clinica=clinica, medico=medico)
    except Cita.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Cita no encontrada.", codigo="no_encontrado"
        ) from exc


def crear_consulta(*, usuario, clinica, datos):
    """Registra la atención y marca la cita atendida de forma atómica."""

    _, medico_inicial = obtener_medico_usuario(
        usuario=usuario,
        clinica=clinica,
    )
    cita_inicial = _obtener_cita_del_medico(
        clinica=clinica,
        medico=medico_inicial,
        cita_id=datos["cita_id"],
    )
    paciente_id = cita_inicial.paciente_id
    medico_id = cita_inicial.medico_id
    personal_id = medico_inicial.personal_id

    with transaction.atomic():
        paciente = obtener_paciente_cita(
            clinica=clinica,
            paciente_id=paciente_id,
            bloquear=True,
        )
        medico = obtener_medico_cita(
            clinica=clinica,
            medico_id=medico_id,
            bloquear=True,
        )
        personal = _obtener_personal_medico(
            clinica=clinica,
            medico=medico,
            bloquear=True,
        )
        cita = _obtener_cita_del_medico(
            clinica=clinica,
            medico=medico,
            cita_id=cita_inicial.pk,
            bloquear=True,
        )

        if (
            paciente.pk != paciente_id
            or medico.pk != medico_id
            or personal.pk != personal_id
            or cita.paciente_id != paciente_id
            or cita.medico_id != medico_id
            or personal.usuario_id != usuario.pk
        ):
            raise RecursoNoEncontrado(
                "Cita no encontrada.", codigo="no_encontrado"
            )

        _validar_recursos_activos(
            paciente=paciente,
            medico=medico,
            personal=personal,
        )
        if Consulta.all_objects.filter(cita=cita).exists():
            raise Conflicto(
                "La cita ya tiene una consulta registrada.",
                codigo="consulta_ya_registrada",
            )
        if cita.estado != EstadoCita.CONFIRMADA:
            raise Conflicto(
                "Solo se puede atender una cita confirmada.",
                codigo="cita_no_confirmada",
            )

        historia = HistoriaClinica.all_objects.select_for_update().filter(
            paciente=paciente,
            paciente__clinica=clinica,
        ).first()
        if historia is None:
            raise Conflicto(
                "El paciente no tiene una historia clínica disponible.",
                codigo="historia_no_disponible",
            )

        consulta = Consulta.all_objects.create(
            clinica=clinica,
            cita=cita,
            medico=medico,
            paciente=paciente,
            motivo=datos["motivo"],
            observacion=datos["observacion"],
            diagnostico=datos["diagnostico"],
        )
        historia.fecha_ultima_actualizacion = timezone.now()
        historia.save(update_fields=["fecha_ultima_actualizacion"])
        cita.estado = EstadoCita.ATENDIDA
        cita.save(update_fields=["estado"])
        EstudioMedico.all_objects.filter(
            clinica=clinica,
            cita=cita,
            consulta__isnull=True,
        ).update(consulta=consulta)
        return consulta


def obtener_consulta_medico(*, usuario, clinica, consulta_id):
    """Obtiene una consulta propia sin revelar otros médicos o tenants."""

    _, medico = obtener_medico_usuario(usuario=usuario, clinica=clinica)
    try:
        return Consulta.all_objects.select_related(
            "cita",
            "paciente",
            "medico__personal",
        ).prefetch_related(
            Prefetch(
                "recetas",
                queryset=Receta.all_objects.prefetch_related(
                    Prefetch(
                        "medicamentos",
                        queryset=MedicamentoRecetado.all_objects.all(),
                    )
                ),
            )
        ).get(
            pk=consulta_id, clinica=clinica, medico=medico
        )
    except Consulta.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Consulta no encontrada.", codigo="no_encontrado"
        ) from exc


def _normalizar_nombre_medicamento(valor):
    return " ".join(unicodedata.normalize("NFKC", valor).split()).casefold()


def calcular_advertencias_alergia(receta):
    """Calcula advertencias actuales sin persistirlas."""
    alergias = Alergia.all_objects.filter(
        historia__paciente_id=receta.consulta.paciente_id,
        historia__paciente__clinica_id=receta.consulta.clinica_id,
        tipo=TipoAlergia.MEDICAMENTO,
    ).order_by("id")
    por_nombre = {}
    for alergia in alergias:
        por_nombre.setdefault(_normalizar_nombre_medicamento(alergia.nombre), []).append(alergia)
    advertencias = []
    for medicamento in receta.medicamentos.all():
        for alergia in por_nombre.get(
            _normalizar_nombre_medicamento(medicamento.nombre_medicamento), ()
        ):
            advertencias.append({
                "alergia_id": alergia.pk,
                "nombre_alergia": alergia.nombre,
                "severidad": alergia.severidad,
                "medicamento": medicamento.nombre_medicamento,
                "mensaje": (
                    f"El medicamento {medicamento.nombre_medicamento} coincide "
                    f"con la alergia medicamentosa {alergia.nombre}."
                ),
            })
    return advertencias


def crear_receta(*, usuario, clinica, consulta_id, datos):
    """Crea receta y medicamentos de forma atómica respetando el orden de bloqueos."""
    _, medico_inicial = obtener_medico_usuario(usuario=usuario, clinica=clinica)
    consulta_inicial = obtener_consulta_medico(
        usuario=usuario, clinica=clinica, consulta_id=consulta_id
    )
    paciente_id = consulta_inicial.paciente_id
    medico_id = consulta_inicial.medico_id
    personal_id = medico_inicial.personal_id
    cita_id = consulta_inicial.cita_id

    with transaction.atomic():
        paciente = obtener_paciente_cita(
            clinica=clinica, paciente_id=paciente_id, bloquear=True
        )
        medico = obtener_medico_cita(
            clinica=clinica, medico_id=medico_id, bloquear=True
        )
        personal = _obtener_personal_medico(
            clinica=clinica, medico=medico, bloquear=True
        )
        if cita_id is None:
            raise Conflicto(
                "La consulta no pertenece a una cita atendida.",
                codigo="consulta_no_atendida",
            )
        cita = _obtener_cita_del_medico(
            clinica=clinica, medico=medico, cita_id=cita_id, bloquear=True
        )
        try:
            consulta = Consulta.all_objects.select_for_update().get(
                pk=consulta_id, clinica=clinica, medico=medico
            )
        except Consulta.DoesNotExist as exc:
            raise RecursoNoEncontrado(
                "Consulta no encontrada.", codigo="no_encontrado"
            ) from exc
        if (
            consulta.paciente_id != paciente.pk
            or consulta.medico_id != medico.pk
            or consulta.cita_id != cita.pk
            or cita.paciente_id != paciente.pk
            or personal.pk != personal_id
            or personal.usuario_id != usuario.pk
        ):
            raise RecursoNoEncontrado(
                "Consulta no encontrada.", codigo="no_encontrado"
            )
        _validar_recursos_activos(paciente=paciente, medico=medico, personal=personal)
        if cita.estado != EstadoCita.ATENDIDA:
            raise Conflicto(
                "Solo se puede emitir una receta para una consulta atendida.",
                codigo="consulta_no_atendida",
            )
        if not HistoriaClinica.all_objects.filter(
            paciente=paciente, paciente__clinica=clinica
        ).exists():
            raise Conflicto(
                "El paciente no tiene una historia clínica disponible.",
                codigo="historia_no_disponible",
            )
        receta = Receta.all_objects.create(
            consulta=consulta, indicaciones=datos.get("indicaciones", "")
        )
        for item in datos["medicamentos"]:
            MedicamentoRecetado.all_objects.create(receta=receta, **item)
        return receta


def obtener_receta_medico(*, usuario, clinica, receta_id):
    _, medico = obtener_medico_usuario(usuario=usuario, clinica=clinica)
    try:
        return Receta.all_objects.select_related(
            "consulta__cita", "consulta__paciente", "consulta__medico__personal"
        ).prefetch_related(
            Prefetch(
                "medicamentos", queryset=MedicamentoRecetado.all_objects.all()
            )
        ).get(
            pk=receta_id,
            consulta__clinica=clinica,
            consulta__medico=medico,
        )
    except Receta.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Receta no encontrada.", codigo="no_encontrado"
        ) from exc


def obtener_cita_sala_virtual(*, usuario, clinica, cita_id):
    """Devuelve la cita virtual si pertenece al médico o paciente autenticado."""

    from .portal_paciente_services import obtener_paciente_autenticado

    queryset = Cita.all_objects.select_related(
        "paciente",
        "medico__personal",
        "medico__especialidad",
        "consulta",
    )

    if tiene_rol(usuario, ROL_MEDICO):
        _, medico = obtener_medico_usuario(usuario=usuario, clinica=clinica)
        cita = queryset.filter(pk=cita_id, clinica=clinica, medico=medico).first()
    else:
        paciente = obtener_paciente_autenticado(usuario=usuario, clinica=clinica)
        cita = queryset.filter(pk=cita_id, clinica=clinica, paciente=paciente).first()

    if cita is None:
        raise RecursoNoEncontrado("Cita no encontrada.", codigo="no_encontrado")
    if cita.modalidad != ModalidadCita.VIRTUAL or not cita.link_videollamada:
        raise Conflicto(
            "La cita seleccionada no tiene modalidad virtual.",
            codigo="cita_no_virtual",
        )
    if cita.estado in (EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO):
        raise Conflicto(
            "La cita no está disponible para videollamada.",
            codigo="cita_no_disponible",
        )
    return cita
