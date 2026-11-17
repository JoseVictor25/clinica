"""Utilidades compartidas por las pruebas de API del Sprint 1."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.clinicas.models import Suscripcion
from apps.personal.models import Especialidad, Medico, Personal
from apps.seguridad.models import Rol, Usuario, UsuarioRol

CLAVE = "ClaveSegura123!"


def crear_usuario_con_rol(
    clinica,
    username,
    rol_nombre=None,
    password=CLAVE,
    estado=True,
    email=None,
):
    usuario = Usuario.objects.create_user(
        username=username,
        email=email or f"{username}@clinica.local",
        password=password,
        clinica=clinica,
        estado=estado,
    )
    if rol_nombre:
        rol = Rol.all_objects.get(clinica=clinica, nombre=rol_nombre)
        UsuarioRol.all_objects.create(usuario=usuario, rol=rol)
    return usuario


def crear_suscripcion(clinica, plan, dias=30, estado=Suscripcion.Estado.ACTIVA):
    hoy = timezone.localdate()
    fecha_inicio = hoy - timedelta(days=1)
    fecha_fin = hoy + timedelta(days=dias)
    if fecha_fin < fecha_inicio:
        fecha_inicio = fecha_fin - timedelta(days=30)
    return Suscripcion.all_objects.create(
        clinica=clinica,
        plan=plan,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=estado,
    )


def token_para(usuario):
    return str(RefreshToken.for_user(usuario).access_token)


def cliente_autenticado(usuario):
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token_para(usuario)}")
    return cliente


def crear_personal_medico(
    clinica,
    usuario,
    ci="CI-MED-001",
    colegiatura="COL-001",
    nombre="Marta",
    apellido="Médica",
):
    especialidad = Especialidad.all_objects.filter(clinica=clinica).first()
    if especialidad is None:
        especialidad = Especialidad.all_objects.create(
            clinica=clinica,
            nombre="Medicina General",
            descripcion="Especialidad de Medicina General.",
        )
    personal = Personal.all_objects.create(
        clinica=clinica,
        usuario=usuario,
        ci=ci,
        nombre=nombre,
        apellido=apellido,
        telefono="70000000",
        cargo="MEDICO",
        fecha_ingreso=timezone.localdate(),
    )
    medico = Medico.all_objects.create(
        clinica=clinica,
        personal=personal,
        especialidad=especialidad,
        numero_colegiatura=colegiatura,
    )
    return personal, medico
