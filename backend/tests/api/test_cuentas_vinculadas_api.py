"""Reglas de identidad y creación de cuentas para Personal y Paciente."""

from datetime import date

import pytest

from apps.core.seed_data import (
    ROL_CONDUCTOR,
    ROL_ENFERMERIA,
    ROL_MEDICO,
    ROL_PACIENTE,
    ROL_RECEPCIONISTA,
)
from apps.pacientes.models import Paciente
from apps.personal.models import Personal
from apps.seguridad.models import Rol, Usuario, UsuarioRol

from .helpers import (
    cliente_autenticado,
    crear_personal_medico,
    crear_usuario_con_rol,
)


def crear_personal(clinica, ci="CI-CUENTA"):
    return Personal.all_objects.create(
        clinica=clinica,
        ci=ci,
        nombre="Ada",
        apellido="Médica",
        telefono="70000001",
        cargo="MEDICO",
        fecha_ingreso=date(2026, 1, 1),
    )


def crear_paciente(clinica, ci="CI-CUENTA"):
    return Paciente.all_objects.create(
        clinica=clinica,
        ci=ci,
        nombre="Ada",
        apellido="Médica",
        sexo="F",
        fecha_nacimiento=date(1990, 1, 1),
        telefono="70000001",
        email="ada@example.com",
    )


@pytest.mark.django_db
def test_crear_cuenta_desde_personal_es_atomico_y_asigna_roles(
    admin_a, clinica_configurada, suscripcion_amplia
):
    personal = crear_personal(clinica_configurada)
    rol = Rol.all_objects.get(clinica=clinica_configurada, nombre=ROL_MEDICO)

    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{personal.pk}/crear-cuenta/",
        {
            "username": "ada_medica",
            "email": "ada.medica@example.com",
            "password": "ClaveSegura123!",
            "roles": [rol.pk],
        },
        format="json",
    )

    assert respuesta.status_code == 201, respuesta.data
    personal.refresh_from_db()
    assert personal.usuario.username == "ada_medica"
    assert respuesta.data["cuenta"]["roles"] == [ROL_MEDICO]


@pytest.mark.django_db
def test_crear_cuenta_paciente_fuerza_rol_y_rechaza_roles_del_cliente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    paciente = crear_paciente(clinica_configurada)
    cliente = cliente_autenticado(admin_a)
    url = f"/api/v1/pacientes/{paciente.pk}/crear-cuenta/"

    invalida = cliente.post(
        url,
        {
            "username": "ada_paciente",
            "email": "ada.paciente@example.com",
            "password": "ClaveSegura123!",
            "roles": [],
        },
        format="json",
    )
    assert invalida.status_code == 400
    assert not Usuario.all_objects.filter(username="ada_paciente").exists()

    creada = cliente.post(
        url,
        {
            "username": "ada_paciente",
            "email": "ada.paciente@example.com",
            "password": "ClaveSegura123!",
        },
        format="json",
    )
    assert creada.status_code == 201, creada.data
    assert creada.data["cuenta"]["roles"] == [ROL_PACIENTE]


@pytest.mark.django_db
def test_vinculos_existentes_exigen_registro_opuesto_y_ci_coincidente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "identidad")
    personal = crear_personal(clinica_configurada, "CI-IGUAL")
    paciente = crear_paciente(clinica_configurada, "CI-IGUAL")
    personal.usuario = usuario
    personal.save(update_fields=["usuario"])

    vinculada = cliente_autenticado(admin_a).post(
        f"/api/v1/pacientes/{paciente.pk}/vincular-usuario/",
        {"usuario_id": usuario.pk},
        format="json",
    )
    assert vinculada.status_code == 200, vinculada.data
    assert UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_PACIENTE
    ).exists()

    otra = crear_personal(clinica_configurada, "CI-DISTINTA")
    rechazo = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{otra.pk}/vincular-usuario/",
        {"usuario_id": usuario.pk},
        format="json",
    )
    assert rechazo.status_code == 409
    assert rechazo.data["codigo"] in {"usuario_ya_vinculado", "identidad_no_coincide"}


@pytest.mark.django_db
def test_cuentas_elegibles_se_filtran_en_backend_por_ci_y_busqueda(
    admin_a, clinica_configurada, suscripcion_amplia
):
    personal = crear_personal(clinica_configurada, "CI-BUSCAR")
    correcto = crear_usuario_con_rol(clinica_configurada, "coincidente")
    paciente = crear_paciente(clinica_configurada, "CI-BUSCAR")
    paciente.usuario = correcto
    paciente.save(update_fields=["usuario"])
    incorrecto = crear_usuario_con_rol(clinica_configurada, "otra_identidad")
    otro_paciente = crear_paciente(clinica_configurada, "CI-OTRA")
    otro_paciente.usuario = incorrecto
    otro_paciente.save(update_fields=["usuario"])

    respuesta = cliente_autenticado(admin_a).get(
        f"/api/v1/personal/{personal.pk}/cuentas-elegibles/",
        {"search": "coinc"},
    )
    assert respuesta.status_code == 200
    assert [item["id"] for item in respuesta.data["results"]] == [correcto.pk]


@pytest.mark.django_db
def test_no_desvincula_cuenta_aunque_tenga_perfil_de_paciente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "multiperfil", ROL_MEDICO)
    personal = crear_personal(clinica_configurada)
    paciente = crear_paciente(clinica_configurada)
    personal.usuario = usuario
    paciente.usuario = usuario
    personal.save(update_fields=["usuario"])
    paciente.save(update_fields=["usuario"])

    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{personal.pk}/vincular-usuario/",
        {"usuario_id": None},
        format="json",
    )
    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "vinculo_personal_permanente"
    personal.refresh_from_db(); paciente.refresh_from_db(); usuario.refresh_from_db()
    assert personal.usuario_id == usuario.pk
    assert paciente.usuario_id == usuario.pk
    assert usuario.estado is True
    assert UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_MEDICO
    ).exists()


@pytest.mark.django_db
def test_no_desvincula_cuenta_si_existe_perfil_medico(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "medico_con_historial", ROL_MEDICO
    )
    personal, _ = crear_personal_medico(
        clinica_configurada,
        usuario,
        ci="CI-NO-CORREGIR",
        colegiatura="COL-NO-CORREGIR",
    )

    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{personal.pk}/vincular-usuario/",
        {"usuario_id": None},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "vinculo_personal_permanente"
    personal.refresh_from_db()
    assert personal.usuario_id == usuario.pk


@pytest.mark.django_db
def test_recepcionista_no_administra_cuentas(
    clinica_configurada, suscripcion_amplia
):
    recepcionista_a = crear_usuario_con_rol(
        clinica_configurada, "recepcion_cuentas", ROL_RECEPCIONISTA
    )
    paciente = crear_paciente(clinica_configurada)
    respuesta = cliente_autenticado(recepcionista_a).post(
        f"/api/v1/pacientes/{paciente.pk}/crear-cuenta/",
        {
            "username": "sin_permiso",
            "email": "sin.permiso@example.com",
            "password": "ClaveSegura123!",
        },
        format="json",
    )
    assert respuesta.status_code == 403
    assert paciente.usuario_id is None


@pytest.mark.django_db
def test_cupo_agotado_revierte_creacion_y_vinculo(
    admin_a, clinica_configurada, suscripcion_a
):
    crear_usuario_con_rol(clinica_configurada, "ocupa_ultimo_cupo")
    personal = crear_personal(clinica_configurada, "CI-SIN-CUPO")

    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{personal.pk}/crear-cuenta/",
        {
            "username": "no_debe_crearse",
            "email": "sin.cupo@example.com",
            "password": "ClaveSegura123!",
            "roles": [],
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "limite_usuarios"
    personal.refresh_from_db()
    assert personal.usuario_id is None
    assert not Usuario.all_objects.filter(username="no_debe_crearse").exists()


@pytest.mark.django_db
def test_no_duplica_cuenta_si_la_misma_ci_ya_tiene_identidad_verificable(
    admin_a, clinica_configurada, suscripcion_amplia
):
    existente = crear_usuario_con_rol(clinica_configurada, "cuenta_existente")
    paciente = crear_paciente(clinica_configurada, "CI-EXISTENTE")
    paciente.usuario = existente
    paciente.save(update_fields=["usuario"])
    personal = crear_personal(clinica_configurada, "CI-EXISTENTE")

    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/personal/{personal.pk}/crear-cuenta/",
        {
            "username": "duplicada",
            "email": "duplicada@example.com",
            "password": "ClaveSegura123!",
            "roles": [],
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "cuenta_existente_verificable"
    assert not Usuario.all_objects.filter(username="duplicada").exists()


@pytest.mark.django_db
def test_cuenta_personal_fuerza_rol_del_cargo_y_rechaza_paciente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    cliente = cliente_autenticado(admin_a)
    paciente_rol = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_PACIENTE
    )
    rechazado = crear_personal(clinica_configurada, "CI-ROL-PACIENTE")

    respuesta = cliente.post(
        f"/api/v1/personal/{rechazado.pk}/crear-cuenta/",
        {
            "username": "rol_paciente_invalido",
            "email": "rol.paciente.invalido@example.com",
            "password": "ClaveSegura123!",
            "roles": [paciente_rol.pk],
        },
        format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["codigo"] == "rol_paciente_no_permitido"
    assert not Usuario.all_objects.filter(username="rol_paciente_invalido").exists()

    personal = crear_personal(clinica_configurada, "CI-ROL-FORZADO")
    creada = cliente.post(
        f"/api/v1/personal/{personal.pk}/crear-cuenta/",
        {
            "username": "rol_forzado",
            "email": "rol.forzado@example.com",
            "password": "ClaveSegura123!",
            "roles": [],
        },
        format="json",
    )
    assert creada.status_code == 201, creada.data
    assert creada.data["cuenta"]["roles"] == [ROL_MEDICO]

    conductor = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_CONDUCTOR
    )
    otro_personal = crear_personal(clinica_configurada, "CI-ROL-AJENO-CARGO")
    rol_ajeno = cliente.post(
        f"/api/v1/personal/{otro_personal.pk}/crear-cuenta/",
        {
            "username": "rol_ajeno_cargo",
            "email": "rol.ajeno.cargo@example.com",
            "password": "ClaveSegura123!",
            "roles": [conductor.pk],
        },
        format="json",
    )
    assert rol_ajeno.status_code == 400
    assert rol_ajeno.data["codigo"] == "rol_no_corresponde_cargo"
    assert not Usuario.all_objects.filter(username="rol_ajeno_cargo").exists()


@pytest.mark.django_db
def test_vincular_personal_activo_agrega_rol_y_el_inactivo_no(
    admin_a, clinica_configurada, suscripcion_amplia
):
    cliente = cliente_autenticado(admin_a)
    activo = crear_personal(clinica_configurada, "CI-VINCULO-ACTIVO")
    usuario_activo = crear_usuario_con_rol(
        clinica_configurada,
        "vinculo_activo",
        estado=False,
    )
    paciente_activo = crear_paciente(clinica_configurada, activo.ci)
    paciente_activo.usuario = usuario_activo
    paciente_activo.save(update_fields=["usuario"])

    respuesta = cliente.post(
        f"/api/v1/personal/{activo.pk}/vincular-usuario/",
        {"usuario_id": usuario_activo.pk},
        format="json",
    )
    assert respuesta.status_code == 200, respuesta.data
    usuario_activo.refresh_from_db()
    assert usuario_activo.estado is True
    assert UsuarioRol.all_objects.filter(
        usuario=usuario_activo, rol__nombre=ROL_MEDICO
    ).exists()

    inactivo = crear_personal(clinica_configurada, "CI-VINCULO-INACTIVO")
    inactivo.estado = False
    inactivo.save(update_fields=["estado"])
    usuario_inactivo = crear_usuario_con_rol(clinica_configurada, "vinculo_inactivo")
    paciente_inactivo = crear_paciente(clinica_configurada, inactivo.ci)
    paciente_inactivo.usuario = usuario_inactivo
    paciente_inactivo.save(update_fields=["usuario"])
    respuesta = cliente.post(
        f"/api/v1/personal/{inactivo.pk}/vincular-usuario/",
        {"usuario_id": usuario_inactivo.pk},
        format="json",
    )
    assert respuesta.status_code == 200, respuesta.data
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario_inactivo, rol__nombre=ROL_MEDICO
    ).exists()


@pytest.mark.django_db
def test_rol_laboral_activo_no_se_puede_quitar_y_expone_proteccion(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "personal_protegido", ROL_RECEPCIONISTA
    )
    personal = crear_personal(clinica_configurada, "CI-PROTEGIDO")
    personal.cargo = "RECEPCION"
    personal.usuario = usuario
    personal.save(update_fields=["cargo", "usuario"])
    asignacion = UsuarioRol.all_objects.get(
        usuario=usuario, rol__nombre=ROL_RECEPCIONISTA
    )
    cliente = cliente_autenticado(admin_a)

    listado = cliente.get("/api/v1/usuario-roles/")
    dato = next(item for item in listado.data["results"] if item["id"] == asignacion.pk)
    assert dato["requerido_por_personal"] is True
    assert "Recepción" in dato["motivo_proteccion"]

    rechazo = cliente.delete(f"/api/v1/usuario-roles/{asignacion.pk}/")
    assert rechazo.status_code == 409
    assert rechazo.data["codigo"] == "rol_requerido_por_personal"

    personal.estado = False
    personal.save(update_fields=["estado"])
    permitido = cliente.delete(f"/api/v1/usuario-roles/{asignacion.pk}/")
    assert permitido.status_code == 204


@pytest.mark.django_db
def test_desactivar_por_edicion_aplica_la_misma_baja_segura(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "conductor_baja", ROL_CONDUCTOR
    )
    personal = crear_personal(clinica_configurada, "CI-BAJA-PATCH")
    personal.cargo = "CONDUCTOR"
    personal.usuario = usuario
    personal.save(update_fields=["cargo", "usuario"])

    respuesta = cliente_autenticado(admin_a).patch(
        f"/api/v1/personal/{personal.pk}/",
        {"estado": False},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
    personal.refresh_from_db()
    usuario.refresh_from_db()
    assert personal.estado is False
    assert personal.usuario_id == usuario.pk
    assert usuario.estado is False
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario,
        rol__nombre=ROL_CONDUCTOR,
    ).exists()


@pytest.mark.django_db
def test_cambio_cargo_reemplaza_rol_y_reactivacion_lo_restaura(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "cambio_cargo", ROL_RECEPCIONISTA
    )
    personal = crear_personal(clinica_configurada, "CI-CAMBIO-CARGO")
    personal.cargo = "RECEPCION"
    personal.usuario = usuario
    personal.estado = False
    personal.save(update_fields=["cargo", "usuario", "estado"])
    cliente = cliente_autenticado(admin_a)

    cambio = cliente.patch(
        f"/api/v1/personal/{personal.pk}/",
        {"cargo": "ENFERMERIA"},
        format="json",
    )
    assert cambio.status_code == 200, cambio.data
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_ENFERMERIA
    ).exists()
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_RECEPCIONISTA
    ).exists()

    reactivado = cliente.patch(
        f"/api/v1/personal/{personal.pk}/",
        {"estado": True},
        format="json",
    )
    assert reactivado.status_code == 200, reactivado.data
    assert UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_ENFERMERIA
    ).exists()


@pytest.mark.django_db
def test_administracion_general_no_asigna_paciente(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(clinica_configurada, "sin_paciente_general")
    paciente_rol = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_PACIENTE
    )
    cliente = cliente_autenticado(admin_a)
    asignacion = cliente.post(
        "/api/v1/usuario-roles/",
        {"usuario": usuario.pk, "rol": paciente_rol.pk},
        format="json",
    )
    assert asignacion.status_code == 400
    assert asignacion.data["codigo"] == "rol_paciente_no_permitido"

    creacion = cliente.post(
        "/api/v1/usuarios/",
        {
            "username": "paciente_general",
            "email": "paciente.general@example.com",
            "password": "ClaveSegura123!",
            "roles": [paciente_rol.pk],
        },
        format="json",
    )
    assert creacion.status_code == 400
    assert creacion.data["codigo"] == "origen_cuenta_requerido"
    assert not Usuario.all_objects.filter(username="paciente_general").exists()


@pytest.mark.django_db
def test_personal_inactivo_puede_cambiar_cargo_pero_no_reactivar_sin_rol(
    admin_a, clinica_configurada, suscripcion_amplia
):
    usuario = crear_usuario_con_rol(
        clinica_configurada, "rollback_laboral", ROL_RECEPCIONISTA
    )
    personal = crear_personal(clinica_configurada, "CI-ROLLBACK-LABORAL")
    personal.cargo = "RECEPCION"
    personal.usuario = usuario
    personal.estado = False
    personal.save(update_fields=["cargo", "usuario", "estado"])
    enfermeria = Rol.all_objects.get(
        clinica=clinica_configurada, nombre=ROL_ENFERMERIA
    )
    enfermeria.estado = False
    enfermeria.save(update_fields=["estado"])
    cliente = cliente_autenticado(admin_a)

    cambio = cliente.patch(
        f"/api/v1/personal/{personal.pk}/",
        {"cargo": "ENFERMERIA"},
        format="json",
    )
    assert cambio.status_code == 200, cambio.data
    personal.refresh_from_db()
    assert personal.cargo == "ENFERMERIA"
    assert personal.estado is False
    assert not UsuarioRol.all_objects.filter(
        usuario=usuario, rol__nombre=ROL_RECEPCIONISTA
    ).exists()

    reactivacion = cliente.patch(
        f"/api/v1/personal/{personal.pk}/",
        {"estado": True},
        format="json",
    )
    assert reactivacion.status_code == 409
    assert reactivacion.data["codigo"] == "rol_obligatorio_no_disponible"
    personal.refresh_from_db()
    assert personal.estado is False
    assert personal.cargo == "ENFERMERIA"
