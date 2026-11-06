"""Servicios de personal, especialidades, médicos y horarios."""

from django.db import IntegrityError, transaction

from apps.core.api_exceptions import Conflicto, DatosInvalidos

from .models import Especialidad, HorarioAtencion, Medico, Personal


def crear_personal(clinica, datos):
    if Personal.all_objects.filter(clinica=clinica, ci=datos["ci"]).exists():
        raise Conflicto(
            "Ya existe personal con esa CI en la clínica.",
            codigo="ci_duplicada",
        )
    try:
        with transaction.atomic():
            return Personal.all_objects.create(clinica=clinica, **datos)
    except IntegrityError as exc:
        raise Conflicto(
            "Ya existe personal con esa CI en la clínica.",
            codigo="ci_duplicada",
        ) from exc


def actualizar_personal(personal, datos):
    ci = datos.get("ci", personal.ci)
    if Personal.all_objects.filter(clinica=personal.clinica, ci=ci).exclude(
        pk=personal.pk
    ).exists():
        raise Conflicto(
            "Ya existe personal con esa CI en la clínica.",
            codigo="ci_duplicada",
        )
    for campo, valor in datos.items():
        setattr(personal, campo, valor)
    personal.save()
    return personal


def vincular_usuario(personal, usuario):
    if usuario is None:
        personal.usuario = None
        personal.save(update_fields=["usuario"])
        return personal

    if usuario.clinica_id != personal.clinica_id:
        raise Conflicto(
            "El usuario debe pertenecer a la misma clínica.",
            codigo="usuario_ajeno",
        )
    if Personal.all_objects.filter(usuario=usuario).exclude(
        pk=personal.pk
    ).exists():
        raise Conflicto(
            "El usuario ya está vinculado a otro registro de personal.",
            codigo="usuario_ya_vinculado",
        )
    personal.usuario = usuario
    personal.save(update_fields=["usuario"])
    return personal


def _validar_personal_y_especialidad(clinica, personal, especialidad):
    if personal.clinica_id != clinica.pk:
        raise Conflicto(
            "El personal no pertenece a la clínica.",
            codigo="personal_ajeno",
        )
    if especialidad.clinica_id != clinica.pk:
        raise Conflicto(
            "La especialidad no pertenece a la clínica.",
            codigo="especialidad_ajena",
        )


def crear_medico(clinica, datos):
    personal = datos["personal"]
    especialidad = datos["especialidad"]
    _validar_personal_y_especialidad(clinica, personal, especialidad)

    if Medico.all_objects.filter(personal=personal).exists():
        raise Conflicto(
            "Ese registro de personal ya tiene un médico asociado.",
            codigo="personal_ya_es_medico",
        )
    if Medico.all_objects.filter(
        numero_colegiatura=datos["numero_colegiatura"]
    ).exists():
        raise Conflicto(
            "La colegiatura ya está registrada.",
            codigo="colegiatura_duplicada",
        )

    try:
        with transaction.atomic():
            return Medico.all_objects.create(clinica=clinica, **datos)
    except IntegrityError as exc:
        raise Conflicto(
            "La colegiatura o el personal ya están registrados.",
            codigo="medico_duplicado",
        ) from exc


def actualizar_medico(medico, datos):
    personal = datos.get("personal", medico.personal)
    especialidad = datos.get("especialidad", medico.especialidad)
    _validar_personal_y_especialidad(medico.clinica, personal, especialidad)

    if Medico.all_objects.filter(personal=personal).exclude(
        pk=medico.pk
    ).exists():
        raise Conflicto(
            "Ese registro de personal ya tiene un médico asociado.",
            codigo="personal_ya_es_medico",
        )
    numero = datos.get("numero_colegiatura", medico.numero_colegiatura)
    if Medico.all_objects.filter(numero_colegiatura=numero).exclude(
        pk=medico.pk
    ).exists():
        raise Conflicto(
            "La colegiatura ya está registrada.",
            codigo="colegiatura_duplicada",
        )

    for campo, valor in datos.items():
        setattr(medico, campo, valor)
    medico.save()
    return medico


def _validar_horas(hora_inicio, hora_fin):
    if hora_inicio >= hora_fin:
        raise DatosInvalidos(
            "La hora de inicio debe ser anterior a la hora de fin.",
            codigo="horario_invalido",
        )


def _validar_solapamiento(medico, dia_semana, hora_inicio, hora_fin, excluir=None):
    qs = HorarioAtencion.all_objects.filter(
        medico=medico,
        dia_semana=dia_semana,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    )
    if excluir is not None:
        qs = qs.exclude(pk=excluir.pk)
    if qs.exists():
        raise Conflicto(
            "El horario se solapa con otro horario del médico.",
            codigo="horario_solapado",
        )


def crear_horario(medico, datos):
    _validar_horas(datos["hora_inicio"], datos["hora_fin"])
    _validar_solapamiento(
        medico,
        datos["dia_semana"],
        datos["hora_inicio"],
        datos["hora_fin"],
    )
    try:
        with transaction.atomic():
            return HorarioAtencion.all_objects.create(medico=medico, **datos)
    except IntegrityError as exc:
        raise Conflicto(
            "El horario ya existe.", codigo="horario_duplicado"
        ) from exc


def actualizar_horario(horario, datos):
    hora_inicio = datos.get("hora_inicio", horario.hora_inicio)
    hora_fin = datos.get("hora_fin", horario.hora_fin)
    dia_semana = datos.get("dia_semana", horario.dia_semana)
    _validar_horas(hora_inicio, hora_fin)
    _validar_solapamiento(
        horario.medico, dia_semana, hora_inicio, hora_fin, excluir=horario
    )
    for campo, valor in datos.items():
        setattr(horario, campo, valor)
    horario.save()
    return horario


def crear_especialidad(clinica, datos):
    if Especialidad.all_objects.filter(
        clinica=clinica, nombre=datos["nombre"]
    ).exists():
        raise Conflicto(
            "Ya existe una especialidad con ese nombre.",
            codigo="especialidad_duplicada",
        )
    return Especialidad.all_objects.create(clinica=clinica, **datos)


def actualizar_especialidad(especialidad, datos):
    nombre = datos.get("nombre", especialidad.nombre)
    if Especialidad.all_objects.filter(
        clinica=especialidad.clinica, nombre=nombre
    ).exclude(pk=especialidad.pk).exists():
        raise Conflicto(
            "Ya existe una especialidad con ese nombre.",
            codigo="especialidad_duplicada",
        )
    for campo, valor in datos.items():
        setattr(especialidad, campo, valor)
    especialidad.save()
    return especialidad
