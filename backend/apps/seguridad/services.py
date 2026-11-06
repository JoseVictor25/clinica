"""Servicios de autenticación, usuarios y roles."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction

from apps.clinicas.services import (
    contar_usuarios_activos,
    suscripcion_vigente,
)
from apps.core.api_exceptions import (
    Conflicto,
    CredencialesInvalidas,
    DatosInvalidos,
    LimiteUsuarios,
    PermisoDenegado,
    SuscripcionVencida,
)
from apps.core.seed_data import ROL_ADMIN_CLINICA

from .models import Rol, Usuario, UsuarioRol


def roles_activos(usuario):
    if not getattr(usuario, "pk", None):
        return []
    return list(
        UsuarioRol.all_objects.filter(usuario=usuario, rol__estado=True)
        .order_by("rol__nombre")
        .values_list("rol__nombre", flat=True)
    )


def tiene_rol(usuario, nombre_rol):
    return nombre_rol in roles_activos(usuario)


def autenticar_usuario(username, password):
    """
    Autentica y aplica la política de suscripción.

    Devuelve (usuario, acceso_restringido).
    """
    usuario = authenticate(username=username, password=password)
    if usuario is None or not usuario.is_active:
        raise CredencialesInvalidas(
            "Usuario o contraseña incorrectos.",
            codigo="credenciales_invalidas",
        )

    if not usuario.clinica_id:
        if not usuario.is_superuser:
            raise PermisoDenegado(
                "El usuario no está asociado a una clínica.",
                codigo="sin_clinica",
            )
        return usuario, False

    if not usuario.clinica.estado:
        raise PermisoDenegado(
            "La clínica está inactiva.", codigo="clinica_inactiva"
        )

    if suscripcion_vigente(usuario.clinica) is None:
        if tiene_rol(usuario, ROL_ADMIN_CLINICA):
            return usuario, True
        raise SuscripcionVencida()

    return usuario, False


def emitir_tokens(usuario, acceso_restringido=False):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(usuario)
    claims = {
        "username": usuario.username,
        "clinica_id": usuario.clinica_id,
        "roles": roles_activos(usuario),
        "acceso_restringido": bool(acceso_restringido),
    }
    for clave, valor in claims.items():
        refresh[clave] = valor

    access = refresh.access_token
    for clave, valor in claims.items():
        access[clave] = valor

    return {"access": str(access), "refresh": str(refresh)}


def cerrar_sesion(refresh_token):
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import RefreshToken

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except (TokenError, AttributeError) as exc:
        raise CredencialesInvalidas(
            "Refresh token inválido.", codigo="refresh_invalido"
        ) from exc


def _validar_password(password, usuario=None):
    try:
        validate_password(password, user=usuario)
    except Exception as exc:
        raise DatosInvalidos(
            "La contraseña no cumple las políticas de seguridad.",
            codigo="password_invalida",
            detalles={"password": list(exc.messages)},
        ) from exc


def _asegurar_cupo(clinica):
    suscripcion = suscripcion_vigente(clinica)
    if suscripcion is None:
        raise SuscripcionVencida()
    activos = contar_usuarios_activos(clinica)
    if activos >= suscripcion.plan.max_usuarios:
        raise LimiteUsuarios(
            "La clínica alcanzó el máximo de usuarios de su plan.",
            codigo="limite_usuarios",
            detalles={
                "usuarios_activos": activos,
                "max_usuarios": suscripcion.plan.max_usuarios,
            },
        )
    return suscripcion


def _asegurar_admin_restante(usuario):
    """Impide desactivar o quitar el rol al último admin activo."""
    if not usuario.clinica_id or not tiene_rol(usuario, ROL_ADMIN_CLINICA):
        return

    otros = UsuarioRol.all_objects.filter(
        rol__clinica_id=usuario.clinica_id,
        rol__nombre=ROL_ADMIN_CLINICA,
        usuario__estado=True,
    ).exclude(usuario=usuario)
    if not otros.exists():
        raise Conflicto(
            "La clínica debe conservar al menos un administrador activo.",
            codigo="ultimo_administrador",
        )


def crear_usuario_clinica(clinica, datos, roles=None, bootstrap=False):
    """
    Crea un usuario de clínica.

    bootstrap=True se usa solo para el primer administrador de S1-01: no
    valida suscripción ni max_usuarios porque la clínica aún no los tiene.
    """
    if not bootstrap:
        _asegurar_cupo(clinica)

    password = datos.pop("password")
    roles = list(roles or [])

    if Usuario.all_objects.filter(username=datos["username"]).exists():
        raise Conflicto(
            "El nombre de usuario no está disponible.",
            codigo="usuario_duplicado",
        )
    if Usuario.all_objects.filter(email=datos["email"]).exists():
        raise Conflicto(
            "El email no está disponible.", codigo="email_duplicado"
        )

    _validar_password(password)
    for rol in roles:
        if rol.clinica_id != clinica.pk:
            raise Conflicto(
                "El rol no pertenece a la clínica.",
                codigo="rol_ajeno",
            )

    try:
        with transaction.atomic():
            if not bootstrap:
                from apps.clinicas.models import Clinica

                Clinica.objects.select_for_update().get(pk=clinica.pk)
                _asegurar_cupo(clinica)

            usuario = Usuario.all_objects.create_user(
                username=datos["username"],
                email=datos["email"],
                password=password,
                clinica=clinica,
                estado=datos.get("estado", True),
                is_staff=False,
            )
            for rol in roles:
                UsuarioRol.all_objects.create(usuario=usuario, rol=rol)
    except IntegrityError as exc:
        raise Conflicto(
            "No se pudo crear el usuario por un conflicto de datos únicos.",
            codigo="usuario_duplicado",
        ) from exc

    return usuario


def actualizar_usuario_clinica(usuario, datos):
    password = datos.pop("password", None)
    if password is not None:
        _validar_password(password, usuario=usuario)

    reactivando = not usuario.estado and datos.get("estado", usuario.estado)
    if usuario.estado and datos.get("estado", usuario.estado) is False:
        _asegurar_admin_restante(usuario)

    try:
        with transaction.atomic():
            if reactivando:
                from apps.clinicas.models import Clinica

                Clinica.objects.select_for_update().get(
                    pk=usuario.clinica_id
                )
                _asegurar_cupo(usuario.clinica)

            for campo, valor in datos.items():
                setattr(usuario, campo, valor)
            if password is not None:
                usuario.set_password(password)
            usuario.save()
    except IntegrityError as exc:
        raise Conflicto(
            "El email no está disponible.", codigo="email_duplicado"
        ) from exc
    return usuario


def desactivar_usuario(usuario):
    _asegurar_admin_restante(usuario)
    usuario.estado = False
    usuario.save(update_fields=["estado"])
    return usuario


def asignar_rol(usuario, rol):
    if usuario.clinica_id != rol.clinica_id:
        raise Conflicto(
            "El usuario y el rol deben pertenecer a la misma clínica.",
            codigo="rol_ajeno",
        )
    if not rol.estado:
        raise Conflicto("El rol está inactivo.", codigo="rol_inactivo")
    if UsuarioRol.all_objects.filter(usuario=usuario, rol=rol).exists():
        raise Conflicto(
            "El rol ya está asignado al usuario.", codigo="rol_ya_asignado"
        )
    return UsuarioRol.all_objects.create(usuario=usuario, rol=rol)


def quitar_rol(usuario_rol):
    if usuario_rol.rol.nombre == ROL_ADMIN_CLINICA:
        _asegurar_admin_restante(usuario_rol.usuario)
    usuario_rol.delete()


def cambiar_password(usuario, password_actual, password_nueva):
    if not usuario.check_password(password_actual):
        raise DatosInvalidos(
            "La contraseña actual no es correcta.",
            codigo="password_actual_invalida",
        )
    if password_actual == password_nueva:
        raise DatosInvalidos(
            "La nueva contraseña debe ser diferente a la actual.",
            codigo="password_repetida",
        )
    _validar_password(password_nueva, usuario=usuario)
    usuario.set_password(password_nueva)
    usuario.save(update_fields=["password"])


def crear_rol(clinica, datos):
    nombre = datos["nombre"]
    if Rol.all_objects.filter(clinica=clinica, nombre=nombre).exists():
        raise Conflicto(
            "Ya existe un rol con ese nombre en la clínica.",
            codigo="rol_duplicado",
        )
    return Rol.all_objects.create(clinica=clinica, **datos)


def actualizar_rol(rol, datos):
    from apps.core.seed_data import ROLES_BASE_NOMBRES

    if rol.nombre in ROLES_BASE_NOMBRES:
        if "nombre" in datos and datos["nombre"] != rol.nombre:
            raise Conflicto(
                "Los roles base no se pueden renombrar.",
                codigo="rol_base_protegido",
            )
        if "estado" in datos and datos["estado"] is False:
            raise Conflicto(
                "Los roles base no se pueden desactivar.",
                codigo="rol_base_protegido",
            )
    if "nombre" in datos and Rol.all_objects.filter(
        clinica=rol.clinica, nombre=datos["nombre"]
    ).exclude(pk=rol.pk).exists():
        raise Conflicto(
            "Ya existe un rol con ese nombre en la clínica.",
            codigo="rol_duplicado",
        )
    for campo, valor in datos.items():
        setattr(rol, campo, valor)
    rol.save()
    return rol


def eliminar_rol(rol):
    from apps.core.seed_data import ROLES_BASE_NOMBRES

    if rol.nombre in ROLES_BASE_NOMBRES:
        raise Conflicto(
            "Los roles base no se pueden eliminar.",
            codigo="rol_base_protegido",
        )
    if UsuarioRol.all_objects.filter(rol=rol).exists():
        raise Conflicto(
            "El rol tiene asignaciones y no se puede eliminar.",
            codigo="rol_con_asignaciones",
        )
    rol.delete()


def perfil_usuario(usuario):
    suscripcion = None
    if usuario.clinica_id:
        suscripcion = suscripcion_vigente(usuario.clinica)

    return {
        "id": usuario.pk,
        "username": usuario.username,
        "email": usuario.email,
        "clinica": usuario.clinica_id,
        "clinica_nombre": usuario.clinica.nombre if usuario.clinica_id else None,
        "roles": roles_activos(usuario),
        "estado": usuario.estado,
        "is_staff": usuario.is_staff,
        "is_superuser": usuario.is_superuser,
        "suscripcion_vigente": suscripcion is not None,
        "suscripcion_fin": suscripcion.fecha_fin if suscripcion else None,
        "acceso_restringido": bool(
            usuario.clinica_id and suscripcion is None
        ),
    }
