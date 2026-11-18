"""Pruebas API de S2-12: vinculación y portal de solo lectura."""

from datetime import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.atencion.models import Cita, Consulta, EstadoCita, MedicamentoRecetado, Receta
from apps.clinicas.models import Suscripcion
from apps.core.seed_data import ROL_MEDICO, ROL_PACIENTE
from apps.core.api_exceptions import Conflicto
from apps.core.tenant import tenant_context
from apps.pacientes.models import Alergia, Enfermedad, HistoriaClinica, Paciente
from apps.personal.models import Personal
from apps.seguridad.models import Rol, UsuarioRol
from apps.pacientes.vinculacion_services import vincular_usuario_paciente
from tests.api.helpers import cliente_autenticado, crear_personal_medico, crear_usuario_con_rol


@pytest.fixture
def portal_contexto(clinica_configurada, paciente_a, usuario_paciente_a, medico_a, suscripcion_amplia):
    paciente_a.usuario = usuario_paciente_a
    paciente_a.save(update_fields=["usuario"])
    historia = HistoriaClinica.all_objects.create(
        paciente=paciente_a, grupo_sanguineo="O+", observaciones_generales="Control anual"
    )
    enfermedad = Enfermedad.all_objects.create(
        historia=historia, nombre="Asma", tipo="CRONICA", severidad="LEVE",
        fecha_deteccion=timezone.localdate(),
    )
    alergia = Alergia.all_objects.create(
        historia=historia, nombre="Penicilina", tipo="MEDICAMENTO", severidad="GRAVE",
        descripcion="Evitar",
    )
    _, medico = crear_personal_medico(
        clinica_configurada, medico_a, ci="MED-PORTAL", colegiatura="COL-PORTAL"
    )
    cita = Cita.all_objects.create(
        clinica=clinica_configurada, paciente=paciente_a, medico=medico,
        fecha=timezone.localdate(), hora=time(9), estado=EstadoCita.ATENDIDA,
        motivo="Control",
    )
    consulta = Consulta.all_objects.create(
        clinica=clinica_configurada, cita=cita, paciente=paciente_a, medico=medico,
        motivo="Control", observacion="Estable", diagnostico="Sin cambios",
    )
    receta = Receta.all_objects.create(consulta=consulta, indicaciones="Con alimentos")
    medicamento = MedicamentoRecetado.all_objects.create(
        receta=receta, nombre_medicamento="Paracetamol", dosis="500 mg",
        frecuencia="Cada 8 horas", duracion="3 días",
    )
    return {
        "usuario": usuario_paciente_a, "paciente": paciente_a, "historia": historia,
        "enfermedad": enfermedad, "alergia": alergia, "medico": medico,
        "cita": cita, "consulta": consulta, "receta": receta,
        "medicamento": medicamento,
    }


@pytest.mark.django_db
def test_admin_vincula_e_idempotencia(admin_a, paciente_a, usuario_paciente_a, suscripcion_amplia):
    Personal.all_objects.create(
        clinica=paciente_a.clinica, usuario=usuario_paciente_a, ci=paciente_a.ci,
        nombre=paciente_a.nombre, apellido=paciente_a.apellido,
        telefono=paciente_a.telefono, cargo="OTRO", fecha_ingreso=timezone.localdate(),
    )
    url = f"/api/v1/pacientes/{paciente_a.pk}/vincular-usuario/"
    cliente = cliente_autenticado(admin_a)
    primera = cliente.post(url, {"usuario_id": usuario_paciente_a.pk}, format="json")
    segunda = cliente.post(url, {"usuario_id": usuario_paciente_a.pk}, format="json")
    esperado = {
        "codigo": "usuario_vinculado", "mensaje": "Usuario vinculado correctamente.",
        "paciente_id": paciente_a.pk, "usuario_id": usuario_paciente_a.pk,
    }
    assert primera.status_code == segunda.status_code == 200
    assert primera.data == segunda.data == esperado
    paciente_a.refresh_from_db()
    assert paciente_a.usuario_id == usuario_paciente_a.pk


@pytest.mark.django_db
def test_vinculacion_valida_permisos_y_cuerpo(admin_a, recepcionista_a, paciente_a, usuario_paciente_a, suscripcion_amplia):
    url = f"/api/v1/pacientes/{paciente_a.pk}/vincular-usuario/"
    assert cliente_autenticado(recepcionista_a).post(url, {"usuario_id": usuario_paciente_a.pk}, format="json").status_code == 403
    respuesta = cliente_autenticado(admin_a).post(url, {"usuario_id": usuario_paciente_a.pk, "clinica_id": 1}, format="json")
    assert respuesta.status_code == 400
    assert "clinica_id" in respuesta.data["detalles"]


@pytest.mark.django_db
def test_vinculacion_asigna_rol_y_rechaza_inactivo(admin_a, paciente_a, clinica_configurada, suscripcion_amplia, datos_paciente):
    usuario = crear_usuario_con_rol(clinica_configurada, "sin_rol_portal")
    Personal.all_objects.create(
        clinica=clinica_configurada, usuario=usuario, ci=paciente_a.ci,
        nombre="Ana", apellido="Pérez", telefono="70000001", cargo="OTRO",
        fecha_ingreso=timezone.localdate(),
    )
    url = f"/api/v1/pacientes/{paciente_a.pk}/vincular-usuario/"
    respuesta = cliente_autenticado(admin_a).post(url, {"usuario_id": usuario.pk}, format="json")
    assert respuesta.status_code == 200
    assert UsuarioRol.all_objects.filter(usuario=usuario, rol__nombre=ROL_PACIENTE).exists()

    inactivo = crear_usuario_con_rol(clinica_configurada, "paciente_inactivo", estado=False)
    otro = Paciente.all_objects.create(
        clinica=clinica_configurada,
        **{**datos_paciente, "ci": "PAC-INACTIVO", "email": "inactivo@example.com"},
    )
    Personal.all_objects.create(
        clinica=clinica_configurada, usuario=inactivo, ci=otro.ci,
        nombre="Otra", apellido="Persona", telefono="70000002", cargo="OTRO",
        fecha_ingreso=timezone.localdate(),
    )
    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/pacientes/{otro.pk}/vincular-usuario/",
        {"usuario_id": inactivo.pk}, format="json",
    )
    assert respuesta.status_code == 400 and respuesta.data["codigo"] == "usuario_no_valido"


@pytest.mark.django_db
def test_vinculacion_rechaza_reemplazo_y_reutilizacion(admin_a, paciente_a, usuario_paciente_a, clinica_configurada, suscripcion_amplia, datos_paciente):
    otro_usuario = crear_usuario_con_rol(clinica_configurada, "paciente_portal_2", ROL_PACIENTE)
    paciente_a.usuario = usuario_paciente_a; paciente_a.save(update_fields=["usuario"])
    url = f"/api/v1/pacientes/{paciente_a.pk}/vincular-usuario/"
    respuesta = cliente_autenticado(admin_a).post(url, {"usuario_id": otro_usuario.pk}, format="json")
    assert respuesta.status_code == 409 and respuesta.data["codigo"] == "paciente_ya_vinculado"
    datos = {**datos_paciente, "ci": "PAC-OTRO", "email": "otro@example.com"}
    otro_paciente = Paciente.all_objects.create(clinica=clinica_configurada, **datos)
    respuesta = cliente_autenticado(admin_a).post(
        f"/api/v1/pacientes/{otro_paciente.pk}/vincular-usuario/",
        {"usuario_id": usuario_paciente_a.pk}, format="json",
    )
    assert respuesta.status_code == 409 and respuesta.data["codigo"] == "usuario_ya_vinculado"


@pytest.mark.django_db
def test_mi_informacion_no_expone_cuenta_ni_clinica(portal_contexto):
    respuesta = cliente_autenticado(portal_contexto["usuario"]).get("/api/v1/portal-paciente/mi-informacion/")
    assert respuesta.status_code == 200
    assert set(respuesta.data) == {"id", "ci", "nombre", "apellido", "sexo", "fecha_nacimiento", "telefono", "email", "estado"}
    assert respuesta.data["id"] == portal_contexto["paciente"].pk


@pytest.mark.django_db
def test_mi_historia_incluye_antecedentes_propios(portal_contexto):
    respuesta = cliente_autenticado(portal_contexto["usuario"]).get("/api/v1/portal-paciente/mi-historia/")
    assert respuesta.status_code == 200
    assert respuesta.data["id"] == portal_contexto["historia"].pk
    assert respuesta.data["enfermedades"][0]["nombre"] == "Asma"
    assert respuesta.data["alergias"][0]["nombre"] == "Penicilina"


@pytest.mark.django_db
def test_historia_ausente_solo_bloquea_mi_historia(portal_contexto):
    portal_contexto["historia"].delete()
    cliente = cliente_autenticado(portal_contexto["usuario"])
    historia = cliente.get("/api/v1/portal-paciente/mi-historia/")
    assert historia.status_code == 409 and historia.data["codigo"] == "historia_no_disponible"
    assert cliente.get("/api/v1/portal-paciente/mi-informacion/").status_code == 200
    assert cliente.get("/api/v1/portal-paciente/mis-citas/").status_code == 200
    assert cliente.get("/api/v1/portal-paciente/mis-consultas/").status_code == 200
    assert cliente.get(f"/api/v1/portal-paciente/mis-recetas/{portal_contexto['receta'].pk}/").status_code == 200


@pytest.mark.django_db
def test_mis_citas_filtros_y_contrato(portal_contexto):
    fecha = timezone.localdate().isoformat()
    respuesta = cliente_autenticado(portal_contexto["usuario"]).get(
        "/api/v1/portal-paciente/mis-citas/",
        {"fecha_desde": fecha, "fecha_hasta": fecha, "estado": "ATENDIDA", "ordering": "fecha"},
    )
    assert respuesta.status_code == 200 and respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["medico"]["especialidad"]
    assert "paciente_id" not in respuesta.data["results"][0]


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/api/v1/portal-paciente/mis-citas/", "/api/v1/portal-paciente/mis-consultas/"])
def test_portal_rechaza_parametros_prohibidos(portal_contexto, url):
    respuesta = cliente_autenticado(portal_contexto["usuario"]).get(url, {"paciente_id": portal_contexto["paciente"].pk})
    assert respuesta.status_code == 400 and respuesta.data["codigo"] == "datos_invalidos"


@pytest.mark.django_db
def test_mis_consultas_y_detalle_receta(portal_contexto):
    cliente = cliente_autenticado(portal_contexto["usuario"])
    consultas = cliente.get("/api/v1/portal-paciente/mis-consultas/")
    assert consultas.status_code == 200 and consultas.data["count"] == 1
    item = consultas.data["results"][0]
    assert item["observacion"] == "Estable" and item["recetas"][0]["id"] == portal_contexto["receta"].pk
    receta = cliente.get(f"/api/v1/portal-paciente/mis-recetas/{portal_contexto['receta'].pk}/")
    assert receta.status_code == 200
    assert receta.data["medicamentos"][0]["nombre_medicamento"] == "Paracetamol"
    assert "advertencias_alergia" not in receta.data


@pytest.mark.django_db
def test_receta_ajena_devuelve_mismo_404(portal_contexto, clinica_configurada, datos_paciente):
    datos = {**datos_paciente, "ci": "PAC-AJENO", "email": "ajeno@example.com"}
    otro = Paciente.all_objects.create(clinica=clinica_configurada, **datos)
    consulta = Consulta.all_objects.create(
        clinica=clinica_configurada, paciente=otro, medico=portal_contexto["medico"],
        motivo="Otro", observacion="Otra", diagnostico="Otro",
    )
    receta = Receta.all_objects.create(consulta=consulta)
    cliente = cliente_autenticado(portal_contexto["usuario"])
    ajena = cliente.get(f"/api/v1/portal-paciente/mis-recetas/{receta.pk}/")
    inexistente = cliente.get("/api/v1/portal-paciente/mis-recetas/999999/")
    assert ajena.status_code == inexistente.status_code == 404
    assert ajena.data == inexistente.data


@pytest.mark.django_db
def test_sin_vinculacion_e_inactivo(portal_contexto):
    paciente = portal_contexto["paciente"]; usuario = portal_contexto["usuario"]
    paciente.usuario = None; paciente.save(update_fields=["usuario"])
    respuesta = cliente_autenticado(usuario).get("/api/v1/portal-paciente/mi-informacion/")
    assert respuesta.status_code == 409 and respuesta.data["codigo"] == "paciente_no_vinculado"
    paciente.usuario = usuario; paciente.estado = False; paciente.save(update_fields=["usuario", "estado"])
    respuesta = cliente_autenticado(usuario).get("/api/v1/portal-paciente/mi-informacion/")
    assert respuesta.status_code == 409 and respuesta.data["codigo"] == "paciente_inactivo"


@pytest.mark.django_db
def test_roles_ajenos_y_anonimo_no_acceden(portal_contexto, cliente, medico_a):
    url = "/api/v1/portal-paciente/mi-informacion/"
    assert cliente.get(url).status_code == 401
    assert cliente_autenticado(medico_a).get(url).status_code == 403


@pytest.mark.django_db
def test_portal_no_permite_escritura(portal_contexto):
    cliente = cliente_autenticado(portal_contexto["usuario"])
    for url in (
        "/api/v1/portal-paciente/mi-informacion/", "/api/v1/portal-paciente/mi-historia/",
        "/api/v1/portal-paciente/mis-citas/", "/api/v1/portal-paciente/mis-consultas/",
        f"/api/v1/portal-paciente/mis-recetas/{portal_contexto['receta'].pk}/",
    ):
        assert cliente.post(url, {}, format="json").status_code == 405


@pytest.mark.django_db
def test_usuario_multirrol_conserva_acceso(portal_contexto):
    usuario = portal_contexto["usuario"]
    rol_medico = Rol.all_objects.get(clinica=usuario.clinica, nombre=ROL_MEDICO)
    UsuarioRol.all_objects.create(usuario=usuario, rol=rol_medico)
    assert cliente_autenticado(usuario).get("/api/v1/portal-paciente/mi-informacion/").status_code == 200


@pytest.mark.django_db
def test_suscripcion_vencida_bloquea_portal(portal_contexto):
    usuario = portal_contexto["usuario"]
    Suscripcion.all_objects.filter(clinica=usuario.clinica).delete()
    respuesta = cliente_autenticado(usuario).get("/api/v1/portal-paciente/mi-informacion/")
    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "suscripcion_vencida"


@pytest.mark.django_db
def test_consultas_no_crecen_por_registro(portal_contexto):
    cliente = cliente_autenticado(portal_contexto["usuario"])
    url = "/api/v1/portal-paciente/mis-consultas/"
    with CaptureQueriesContext(connection) as pocas:
        assert cliente.get(url).status_code == 200
    for numero in range(5):
        consulta = Consulta.all_objects.create(
            clinica=portal_contexto["paciente"].clinica,
            paciente=portal_contexto["paciente"], medico=portal_contexto["medico"],
            motivo=f"Control {numero}", observacion="Estable", diagnostico="Control",
        )
        receta = Receta.all_objects.create(consulta=consulta)
        MedicamentoRecetado.all_objects.create(
            receta=receta, nombre_medicamento=f"M{numero}", dosis="1",
            frecuencia="Diaria", duracion="1 día",
        )
    with CaptureQueriesContext(connection) as muchas:
        respuesta = cliente.get(url)
    assert respuesta.status_code == 200 and respuesta.data["count"] == 6
    assert len(muchas) <= len(pocas) + 1


def _vincular_conexion_independiente(clinica, paciente_id, usuario_id, barrera):
    close_old_connections()
    try:
        with tenant_context(clinica):
            barrera.wait(timeout=5)
            paciente = vincular_usuario_paciente(
                clinica=clinica, paciente_id=paciente_id, usuario_id=usuario_id
            )
            return ("vinculado", paciente.pk)
    except Conflicto as error:
        return ("conflicto", error.codigo)
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_concurrencia_vinculacion_idempotente_del_mismo_paciente(
    clinica_configurada, paciente_a, usuario_paciente_a
):
    assert connection.vendor == "postgresql"
    Personal.all_objects.create(
        clinica=clinica_configurada, usuario=usuario_paciente_a, ci=paciente_a.ci,
        nombre="Ana", apellido="Pérez", telefono="70000001", cargo="OTRO",
        fecha_ingreso=timezone.localdate(),
    )
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(
            lambda paciente_id: _vincular_conexion_independiente(
                clinica_configurada, paciente_id, usuario_paciente_a.pk, barrera
            ),
            [paciente_a.pk, paciente_a.pk],
        ))
    assert [item[0] for item in resultados] == ["vinculado", "vinculado"]
    assert Paciente.all_objects.filter(usuario=usuario_paciente_a).count() == 1
