"""Rutas de clínicas, planes y suscripciones."""

from rest_framework.routers import DefaultRouter

from .views import ClinicaViewSet, PlanSuscripcionViewSet, SuscripcionViewSet

router = DefaultRouter()
router.register("clinicas", ClinicaViewSet, basename="clinica")
router.register("planes", PlanSuscripcionViewSet, basename="plan")
router.register("suscripciones", SuscripcionViewSet, basename="suscripcion")

urlpatterns = router.urls
