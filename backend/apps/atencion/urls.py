"""Rutas de citas y atención."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .estudios_views import EstudioMedicoViewSet
from .views import (
    CitaViewSet,
    ConsultaViewSet,
    MiAgendaMedicoView,
    RecetaCrearView,
    RecetaDetalleView,
    SalaVirtualCitaView,
)
from .portal_paciente_views import (
    MiHistoriaView,
    MiInformacionView,
    MiRecetaDetalleView,
    MisCitasView,
    MisConsultasView,
)

router = DefaultRouter()
router.register("citas", CitaViewSet, basename="cita")
router.register("consultas", ConsultaViewSet, basename="consulta")
router.register("estudios-medicos", EstudioMedicoViewSet, basename="estudio-medico")

urlpatterns = [
    path("portal-paciente/mi-informacion/", MiInformacionView.as_view(), name="portal-mi-informacion"),
    path("portal-paciente/mi-historia/", MiHistoriaView.as_view(), name="portal-mi-historia"),
    path("portal-paciente/mis-citas/", MisCitasView.as_view(), name="portal-mis-citas"),
    path("portal-paciente/mis-consultas/", MisConsultasView.as_view(), name="portal-mis-consultas"),
    path("portal-paciente/mis-recetas/<int:pk>/", MiRecetaDetalleView.as_view(), name="portal-mi-receta"),
    path("citas/mi-agenda/", MiAgendaMedicoView.as_view(), name="mi-agenda"),
    path(
        "citas/<int:pk>/sala-virtual/",
        SalaVirtualCitaView.as_view(),
        name="cita-sala-virtual",
    ),
    path(
        "consultas/<int:consulta_id>/recetas/",
        RecetaCrearView.as_view(),
        name="receta-crear",
    ),
    path("recetas/<int:pk>/", RecetaDetalleView.as_view(), name="receta-detalle"),
    *router.urls,
]

