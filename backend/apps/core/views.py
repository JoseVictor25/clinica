"""Vistas utilitarias del proyecto (salud y raíz)."""

from django.http import JsonResponse
from django.shortcuts import redirect


def health(request):
    """
    Endpoint de salud sin dependencia de tenant ni de base de datos.

    Permite comprobar que el proceso responde sin iniciar sesión y sin que el
    middleware tenant necesite resolver una clínica.
    """
    return JsonResponse({"status": "ok"})


def raiz(request):
    """Redirige la raíz a la documentación interactiva de la API."""
    return redirect("/api/docs/")
