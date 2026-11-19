"""Resolución tenant-safe y consultas del portal del paciente."""

from django.db.models import Prefetch

from apps.core.api_exceptions import Conflicto, RecursoNoEncontrado
from apps.core.permissions import tiene_rol
from apps.core.seed_data import ROL_PACIENTE
from apps.pacientes.models import Alergia, Enfermedad, HistoriaClinica, Paciente

from .models import Cita, Consulta, EstudioMedico, MedicamentoRecetado, Receta


def obtener_paciente_autenticado(*, usuario, clinica):
    if not usuario.estado or usuario.clinica_id != clinica.pk or not tiene_rol(usuario, ROL_PACIENTE):
        raise Conflicto("El usuario no está vinculado a un paciente válido.", codigo="paciente_no_vinculado")
    paciente = Paciente.all_objects.filter(usuario=usuario, clinica=clinica).first()
    if paciente is None:
        raise Conflicto("El usuario no está vinculado a un paciente.", codigo="paciente_no_vinculado")
    if not paciente.estado:
        raise Conflicto("El paciente está inactivo.", codigo="paciente_inactivo")
    return paciente


def obtener_historia_portal(*, paciente, clinica):
    historia = (
        HistoriaClinica.all_objects.filter(paciente=paciente, paciente__clinica=clinica)
        .prefetch_related(
            Prefetch("enfermedades", queryset=Enfermedad.all_objects.order_by("-fecha_deteccion", "-id")),
            Prefetch("alergias", queryset=Alergia.all_objects.order_by("nombre", "id")),
        )
        .first()
    )
    if historia is None:
        raise Conflicto("El paciente no tiene una historia clínica disponible.", codigo="historia_no_disponible")
    return historia


def obtener_citas_portal(*, paciente, clinica, filtros):
    queryset = Cita.all_objects.filter(clinica=clinica, paciente=paciente).select_related(
        "medico__personal", "medico__especialidad"
    )
    if filtros.get("fecha_desde"):
        queryset = queryset.filter(fecha__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        queryset = queryset.filter(fecha__lte=filtros["fecha_hasta"])
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    orden = filtros.get("ordering", "-fecha")
    return queryset.order_by(orden, "hora" if orden == "fecha" else "-hora", "id" if orden == "fecha" else "-id")


def obtener_consultas_portal(*, paciente, clinica, filtros):
    recetas = Receta.all_objects.prefetch_related(
        Prefetch("medicamentos", queryset=MedicamentoRecetado.all_objects.order_by("id"))
    ).order_by("-fecha", "-id")
    estudios = EstudioMedico.all_objects.order_by("-fecha_estudio", "-id")
    queryset = Consulta.all_objects.filter(clinica=clinica, paciente=paciente).select_related(
        "cita", "medico__personal", "medico__especialidad"
    ).prefetch_related(
        Prefetch("recetas", queryset=recetas),
        Prefetch("estudios_medicos", queryset=estudios),
    )
    if filtros.get("fecha_desde"):
        queryset = queryset.filter(fecha__date__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        queryset = queryset.filter(fecha__date__lte=filtros["fecha_hasta"])
    orden = filtros.get("ordering", "-fecha")
    return queryset.order_by(orden, "id" if orden == "fecha" else "-id")


def obtener_receta_portal(*, receta_id, paciente, clinica):
    receta = (
        Receta.all_objects.filter(
            pk=receta_id,
            consulta__clinica=clinica,
            consulta__paciente=paciente,
        )
        .select_related("consulta", "consulta__medico__personal", "consulta__medico__especialidad")
        .prefetch_related(Prefetch("medicamentos", queryset=MedicamentoRecetado.all_objects.order_by("id")))
        .first()
    )
    if receta is None:
        raise RecursoNoEncontrado("El recurso no existe o no pertenece al paciente.")
    return receta
