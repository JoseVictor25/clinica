"""Rutas de personal, especialidades, médicos y horarios."""

from rest_framework.routers import DefaultRouter

from .views import (
    EspecialidadViewSet,
    HorarioAtencionViewSet,
    MedicoViewSet,
    PersonalViewSet,
)

router = DefaultRouter()
router.register("personal", PersonalViewSet, basename="personal")
router.register("especialidades", EspecialidadViewSet, basename="especialidad")
router.register("medicos", MedicoViewSet, basename="medico")
router.register("horarios", HorarioAtencionViewSet, basename="horario")

urlpatterns = router.urls
