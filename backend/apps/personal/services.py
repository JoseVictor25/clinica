"""Servicios de personal, especialidades, médicos y horarios."""

from django.db import IntegrityError, transaction

from apps.core.api_exceptions import Conflicto, DatosInvalidos, RecursoNoEncontrado
from apps.core.identidad import CAMPOS_IDENTIDAD, copiar_identidad
from apps.core.seed_data import ROL_PACIENTE
from apps.pacientes.models import Paciente
from apps.seguridad.models import Rol, Usuario, UsuarioRol
from apps.seguridad.services import actualizar_usuario_clinica

from .models import Especialidad, HorarioAtencion, Medico, Personal
from .role_policy import garantizar_rol_obligatorio, retirar_rol_del_cargo


def crear_personal(clinica, datos):
    if Personal.all_objects.filter(clinica=clinica, ci=datos["ci"]).exists():
        raise Conflicto(
            "Ya existe personal con esa CI en la clínica.",
            codigo="ci_duplicada",
        )
    try:
        with transaction.atomic():
            paciente = (
                Paciente.all_objects.select_for_update()
                .filter(clinica=clinica, ci=datos["ci"])
                .first()
            )
            if paciente is not None:
                copiar_identidad(datos, paciente)
            return Personal.all_objects.create(clinica=clinica, **datos)
    except IntegrityError as exc:
        raise Conflicto(
            "Ya existe personal con esa CI en la clínica.",
            codigo="ci_duplicada",
        ) from exc


def actualizar_personal(personal, datos):
    with transaction.atomic():
        bloqueado = (
            Personal.all_objects.select_for_update()
            .select_related("clinica")
            .get(pk=personal.pk)
        )
        ci = datos.get("ci", bloqueado.ci)
        if ci != bloqueado.ci:
            raise DatosInvalidos(
                "La CI no puede modificarse porque identifica a la persona.",
                codigo="ci_no_modificable",
                detalles={"ci": ["La CI no puede modificarse."]},
            )
        if Personal.all_objects.filter(
            clinica=bloqueado.clinica, ci=ci
        ).exclude(pk=bloqueado.pk).exists():
            raise Conflicto(
                "Ya existe personal con esa CI en la clínica.",
                codigo="ci_duplicada",
            )

        cargo_nuevo = datos.get("cargo", bloqueado.cargo)
        estado_nuevo = datos.get("estado", bloqueado.estado)
        cambio_cargo = cargo_nuevo != bloqueado.cargo
        reactivando = not bloqueado.estado and estado_nuevo
        desactivando = bloqueado.estado and not estado_nuevo
        if desactivando:
            _finalizar_bloqueado(bloqueado)
            for campo, valor in datos.items():
                if campo != "estado":
                    setattr(bloqueado, campo, valor)
            bloqueado.save()
            _sincronizar_identidad_con_paciente(bloqueado)
            return bloqueado
        if bloqueado.usuario_id and estado_nuevo and (cambio_cargo or reactivando):
            usuario = Usuario.all_objects.select_for_update().get(
                pk=bloqueado.usuario_id
            )
            rol_nuevo = garantizar_rol_obligatorio(
                clinica=bloqueado.clinica,
                cargo=cargo_nuevo,
                usuario=usuario,
                bloquear=True,
            )
            if rol_nuevo is not None and not usuario.estado:
                actualizar_usuario_clinica(usuario, {"estado": True})
            if cambio_cargo:
                retirar_rol_del_cargo(
                    clinica=bloqueado.clinica,
                    cargo=bloqueado.cargo,
                    usuario=usuario,
                )
                _desactivar_usuario_sin_roles_activos(usuario)
        elif bloqueado.usuario_id and cambio_cargo and not estado_nuevo:
            usuario = Usuario.all_objects.select_for_update().get(
                pk=bloqueado.usuario_id
            )
            retirar_rol_del_cargo(
                clinica=bloqueado.clinica,
                cargo=bloqueado.cargo,
                usuario=usuario,
            )
            _desactivar_usuario_sin_roles_activos(usuario)

        for campo, valor in datos.items():
            setattr(bloqueado, campo, valor)
        bloqueado.save()
        _sincronizar_identidad_con_paciente(bloqueado)
        if reactivando and cargo_nuevo == "MEDICO":
            Medico.all_objects.filter(personal=bloqueado).update(estado=True)
        return bloqueado


def _sincronizar_identidad_con_paciente(personal):
    paciente = (
        Paciente.all_objects.select_for_update()
        .filter(clinica=personal.clinica, ci=personal.ci)
        .first()
    )
    if paciente is None:
        return
    cambios = {
        campo: getattr(personal, campo)
        for campo in CAMPOS_IDENTIDAD
        if getattr(paciente, campo) != getattr(personal, campo)
    }
    if cambios:
        Paciente.all_objects.filter(pk=paciente.pk).update(**cambios)


def _desactivar_usuario_sin_roles_activos(usuario):
    paciente_activo = Paciente.all_objects.filter(
        usuario=usuario,
        estado=True,
    ).exists()
    if paciente_activo:
        rol_paciente = Rol.all_objects.filter(
            clinica=usuario.clinica,
            nombre=ROL_PACIENTE,
            estado=True,
        ).first()
        if rol_paciente is not None:
            UsuarioRol.all_objects.get_or_create(
                usuario=usuario,
                rol=rol_paciente,
            )
    tiene_roles_activos = UsuarioRol.all_objects.filter(
        usuario=usuario,
        rol__estado=True,
    ).exists()
    if not tiene_roles_activos and usuario.estado:
        usuario.estado = False
        usuario.save(update_fields=["estado"])


def _finalizar_bloqueado(bloqueado):
    usuario = None
    if bloqueado.usuario_id:
        usuario = Usuario.all_objects.select_for_update().get(
            pk=bloqueado.usuario_id
        )

    bloqueado.estado = False
    bloqueado.save(update_fields=["estado"])
    Medico.all_objects.select_for_update().filter(
        personal=bloqueado
    ).update(estado=False)

    if usuario is not None:
        retirar_rol_del_cargo(
            clinica=bloqueado.clinica,
            cargo=bloqueado.cargo,
            usuario=usuario,
        )
        _desactivar_usuario_sin_roles_activos(usuario)
    return bloqueado


def finalizar_relacion_laboral(personal):
    """Finaliza el acceso laboral conservando identidad e historial."""
    with transaction.atomic():
        bloqueado = (
            Personal.all_objects.select_for_update()
            .select_related("clinica")
            .get(pk=personal.pk)
        )
        return _finalizar_bloqueado(bloqueado)


def vincular_usuario(personal, usuario):
    """Vincula una cuenta cuya identidad ya fue verificada por Paciente."""
    with transaction.atomic():
        bloqueado = Personal.all_objects.select_for_update().get(pk=personal.pk)
        if usuario is None:
            raise Conflicto(
                "El vínculo entre Personal y Usuario es permanente. Usa Finalizar relación para una baja laboral.",
                codigo="vinculo_personal_permanente",
            )

        usuario_bloqueado = (
            Usuario.all_objects.select_for_update()
            .filter(pk=usuario.pk, clinica=bloqueado.clinica)
            .first()
        )
        if usuario_bloqueado is None:
            raise RecursoNoEncontrado("Usuario no encontrado.")

        # Los vínculos creados antes de esta regla siguen siendo idempotentes.
        if bloqueado.usuario_id == usuario_bloqueado.pk:
            if bloqueado.estado:
                garantizar_rol_obligatorio(
                    clinica=bloqueado.clinica,
                    cargo=bloqueado.cargo,
                    usuario=usuario_bloqueado,
                    bloquear=True,
                )
            return bloqueado
        if bloqueado.usuario_id is not None:
            raise Conflicto(
                "El personal ya está vinculado a otra cuenta.",
                codigo="personal_ya_vinculado",
            )
        if Personal.all_objects.filter(usuario=usuario_bloqueado).exclude(
            pk=bloqueado.pk
        ).exists():
            raise Conflicto(
                "El usuario ya está vinculado a otro registro de personal.",
                codigo="usuario_ya_vinculado",
            )

        identidad = Paciente.all_objects.filter(
            clinica=bloqueado.clinica,
            ci=bloqueado.ci,
            usuario=usuario_bloqueado,
        ).exists()
        if not identidad:
            raise Conflicto(
                "La cuenta debe estar vinculada a un paciente con la misma CI.",
                codigo="identidad_no_coincide",
            )

        if bloqueado.estado:
            if not usuario_bloqueado.estado:
                actualizar_usuario_clinica(
                    usuario_bloqueado,
                    {"estado": True},
                )
            garantizar_rol_obligatorio(
                clinica=bloqueado.clinica,
                cargo=bloqueado.cargo,
                usuario=usuario_bloqueado,
                bloquear=True,
            )

        bloqueado.usuario = usuario_bloqueado
        bloqueado.save(update_fields=["usuario"])
        return bloqueado


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


def _normalizar_especialidades(clinica, principal, especialidades):
    asignadas = {especialidad.pk: especialidad for especialidad in especialidades}
    asignadas[principal.pk] = principal
    for especialidad in asignadas.values():
        if especialidad.clinica_id != clinica.pk:
            raise Conflicto(
                "Una especialidad no pertenece a la clínica.",
                codigo="especialidad_ajena",
            )
    return list(asignadas.values())


def crear_medico(clinica, datos):
    especialidades = datos.pop("especialidades", [])
    personal = datos["personal"]
    especialidad = datos["especialidad"]
    _validar_personal_y_especialidad(clinica, personal, especialidad)
    especialidades = _normalizar_especialidades(
        clinica, especialidad, especialidades
    )

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
            medico = Medico.all_objects.create(clinica=clinica, **datos)
            medico.especialidades.set(especialidades)
            return medico
    except IntegrityError as exc:
        raise Conflicto(
            "La colegiatura o el personal ya están registrados.",
            codigo="medico_duplicado",
        ) from exc


def actualizar_medico(medico, datos):
    especialidades = datos.pop("especialidades", None)
    personal = datos.get("personal", medico.personal)
    especialidad = datos.get("especialidad", medico.especialidad)
    _validar_personal_y_especialidad(medico.clinica, personal, especialidad)
    if especialidades is None:
        especialidades = list(medico.especialidades.all())
    especialidades = _normalizar_especialidades(
        medico.clinica, especialidad, especialidades
    )

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

    with transaction.atomic():
        for campo, valor in datos.items():
            setattr(medico, campo, valor)
        medico.save()
        medico.especialidades.set(especialidades)
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
