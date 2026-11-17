"""Servicios y reglas de negocio de pacientes y antecedentes clínicos."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.api_exceptions import (
    Conflicto,
    DatosInvalidos,
    RecursoNoEncontrado,
)

from .models import Alergia, Enfermedad, HistoriaClinica, Paciente

RESTRICCION_ALERGIA_UNICA = "uniq_alergia_por_historia"


def _validar_fecha_nacimiento(fecha):
    if fecha and fecha > timezone.localdate():
        mensaje = "La fecha de nacimiento no puede ser futura."
        raise DatosInvalidos(
            mensaje,
            codigo="fecha_nacimiento_invalida",
            detalles={"fecha_nacimiento": [mensaje]},
        )


def _conflicto_ci():
    return Conflicto(
        "Ya existe un paciente con esa CI en la clínica.",
        codigo="ci_duplicada",
    )


def _existe_ci(clinica, ci):
    return Paciente.all_objects.filter(clinica=clinica, ci=ci).exists()


def crear_paciente(clinica, datos):
    _validar_fecha_nacimiento(datos.get("fecha_nacimiento"))
    if _existe_ci(clinica, datos["ci"]):
        raise _conflicto_ci()

    with transaction.atomic():
        # El savepoint permite traducir solo el conflicto del paciente.
        # Un fallo posterior al crear la historia se propaga y revierte
        # también al paciente mediante la transacción exterior.
        try:
            with transaction.atomic():
                paciente = Paciente.all_objects.create(
                    clinica=clinica,
                    **datos,
                )
        except IntegrityError as exc:
            raise _conflicto_ci() from exc

        HistoriaClinica.all_objects.create(paciente=paciente)
        return paciente


def actualizar_paciente(paciente, datos):
    _validar_fecha_nacimiento(
        datos.get("fecha_nacimiento", paciente.fecha_nacimiento)
    )
    ci = datos.get("ci", paciente.ci)
    duplicado = (
        Paciente.all_objects.filter(clinica=paciente.clinica, ci=ci)
        .exclude(pk=paciente.pk)
        .exists()
    )
    if duplicado:
        raise _conflicto_ci()

    try:
        with transaction.atomic():
            for campo, valor in datos.items():
                setattr(paciente, campo, valor)
            paciente.save()
            return paciente
    except IntegrityError as exc:
        raise _conflicto_ci() from exc


def desactivar_paciente(paciente):
    if paciente.estado:
        paciente.estado = False
        paciente.save(update_fields=["estado"])
    return paciente


def obtener_historia_paciente(paciente):
    """Obtiene la historia del paciente ya restringido al tenant."""
    historia = HistoriaClinica.all_objects.filter(paciente=paciente).first()
    if historia is None:
        raise Conflicto(
            "El paciente no tiene una historia clínica disponible.",
            codigo="historia_no_disponible",
        )
    return historia


def _validar_fecha_deteccion(fecha):
    if fecha and fecha > timezone.localdate():
        mensaje = "La fecha de detección no puede ser futura."
        raise DatosInvalidos(
            mensaje,
            codigo="fecha_deteccion_invalida",
            detalles={"fecha_deteccion": [mensaje]},
        )


def crear_enfermedad(historia, datos):
    """Registra una enfermedad sin permitir elegir otra historia."""
    _validar_fecha_deteccion(datos.get("fecha_deteccion"))
    with transaction.atomic():
        return Enfermedad.all_objects.create(historia=historia, **datos)


def actualizar_enfermedad(enfermedad, datos):
    """Actualiza solo datos clínicos y conserva la historia original."""
    _validar_fecha_deteccion(
        datos.get("fecha_deteccion", enfermedad.fecha_deteccion)
    )
    with transaction.atomic():
        for campo, valor in datos.items():
            setattr(enfermedad, campo, valor)
        enfermedad.save()
        return enfermedad


def _conflicto_alergia():
    return Conflicto(
        "Ya existe una alergia con ese nombre en la historia clínica.",
        codigo="alergia_duplicada",
    )


def _restriccion_integridad(exc):
    """Extrae la restricción PostgreSQL sin clasificar otros fallos."""
    diagnostico = getattr(getattr(exc, "__cause__", None), "diag", None)
    return getattr(diagnostico, "constraint_name", None)


def _normalizar_nombre_alergia(datos):
    datos = dict(datos)
    if "nombre" in datos:
        datos["nombre"] = datos["nombre"].strip()
        if not datos["nombre"]:
            mensaje = "El nombre es obligatorio."
            raise DatosInvalidos(
                mensaje,
                detalles={"nombre": [mensaje]},
            )
    return datos


def _existe_alergia(historia, nombre, excluir_id=None):
    consulta = Alergia.all_objects.filter(
        historia=historia,
        nombre=nombre,
    )
    if excluir_id is not None:
        consulta = consulta.exclude(pk=excluir_id)
    return consulta.exists()


def crear_alergia(historia, datos):
    """Crea una alergia y traduce solo su restricción de unicidad."""
    datos = _normalizar_nombre_alergia(datos)
    if _existe_alergia(historia, datos["nombre"]):
        raise _conflicto_alergia()

    try:
        with transaction.atomic():
            return Alergia.all_objects.create(historia=historia, **datos)
    except IntegrityError as exc:
        if _restriccion_integridad(exc) == RESTRICCION_ALERGIA_UNICA:
            raise _conflicto_alergia() from exc
        raise


def actualizar_alergia(alergia, datos):
    """Actualiza una alergia conservando la historia original."""
    datos = _normalizar_nombre_alergia(datos)
    nombre = datos.get("nombre", alergia.nombre)
    if _existe_alergia(alergia.historia, nombre, alergia.pk):
        raise _conflicto_alergia()

    try:
        with transaction.atomic():
            for campo, valor in datos.items():
                setattr(alergia, campo, valor)
            alergia.save()
            return alergia
    except IntegrityError as exc:
        if _restriccion_integridad(exc) == RESTRICCION_ALERGIA_UNICA:
            raise _conflicto_alergia() from exc
        raise


def obtener_historial_consultas(*, usuario, clinica, paciente_id, filtros):
    """Construye en lectura el historial tenant-safe de un paciente."""

    from django.db.models import Prefetch

    from apps.atencion.models import Consulta, MedicamentoRecetado, Receta
    from apps.atencion.services import obtener_medico_usuario
    from apps.personal.models import Medico

    _, medico_autenticado = obtener_medico_usuario(usuario=usuario, clinica=clinica)
    try:
        paciente = Paciente.all_objects.get(pk=paciente_id, clinica=clinica)
    except Paciente.DoesNotExist as exc:
        raise RecursoNoEncontrado(
            "Paciente no encontrado.", codigo="no_encontrado"
        ) from exc
    if not paciente.estado:
        raise Conflicto(
            "El paciente está inactivo.", codigo="paciente_inactivo"
        )
    obtener_historia_paciente(paciente)

    medico_id = filtros.get("medico_id")
    if medico_id is not None and not Medico.all_objects.filter(
        pk=medico_id, clinica=clinica
    ).exists():
        raise RecursoNoEncontrado(
            "Médico no encontrado.", codigo="no_encontrado"
        )

    recetas = Receta.all_objects.select_related("consulta").prefetch_related(
        Prefetch(
            "medicamentos",
            queryset=MedicamentoRecetado.all_objects.order_by("id"),
        )
    ).order_by("-fecha", "-id")
    consultas = Consulta.all_objects.filter(
        clinica=clinica, paciente=paciente
    ).select_related(
        "cita", "medico__personal", "medico__especialidad"
    ).prefetch_related(Prefetch("recetas", queryset=recetas))

    if filtros.get("fecha_desde"):
        consultas = consultas.filter(fecha__date__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        consultas = consultas.filter(fecha__date__lte=filtros["fecha_hasta"])
    if medico_id is not None:
        consultas = consultas.filter(medico_id=medico_id)

    ordering = filtros.get("ordering", "-fecha")
    desempate = "id" if ordering == "fecha" else "-id"
    return paciente, medico_autenticado, consultas.order_by(ordering, desempate)
