from django.urls import path

from .views import DispositivoPushView, NotificacionLeerView, NotificacionesView

urlpatterns = [
    path("notificaciones/", NotificacionesView.as_view(), name="notificaciones"),
    path("notificaciones/<int:pk>/leer/", NotificacionLeerView.as_view(), name="notificacion-leer"),
    path("notificaciones/dispositivos/", DispositivoPushView.as_view(), name="dispositivos-push"),
]
