from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AlergiaViewSet,
    EnfermedadViewSet,
    HistorialConsultasPacienteView,
    PacienteViewSet,
)

router = DefaultRouter()
router.register("pacientes", PacienteViewSet, basename="paciente")

enfermedades_lista = EnfermedadViewSet.as_view(
    {"get": "list", "post": "create"}
)
enfermedades_detalle = EnfermedadViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update"}
)
alergias_lista = AlergiaViewSet.as_view(
    {"get": "list", "post": "create"}
)
alergias_detalle = AlergiaViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update"}
)

urlpatterns = [
    path(
        "pacientes/<int:paciente_id>/historial-consultas/",
        HistorialConsultasPacienteView.as_view(),
        name="paciente-historial-consultas",
    ),
    path(
        "pacientes/<int:paciente_id>/enfermedades/",
        enfermedades_lista,
        name="paciente-enfermedades",
    ),
    path(
        "pacientes/<int:paciente_id>/enfermedades/<int:enfermedad_id>/",
        enfermedades_detalle,
        name="paciente-enfermedad-detalle",
    ),
    path(
        "pacientes/<int:paciente_id>/alergias/",
        alergias_lista,
        name="paciente-alergias",
    ),
    path(
        "pacientes/<int:paciente_id>/alergias/<int:alergia_id>/",
        alergias_detalle,
        name="paciente-alergia-detalle",
    ),
    *router.urls,
]
