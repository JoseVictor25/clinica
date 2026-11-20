from django.db import migrations


def vincular_identidades_personal(apps, schema_editor):
    Paciente = apps.get_model("pacientes", "Paciente")
    Personal = apps.get_model("personal", "Personal")
    Rol = apps.get_model("seguridad", "Rol")
    UsuarioRol = apps.get_model("seguridad", "UsuarioRol")

    for paciente in Paciente._base_manager.filter(usuario__isnull=True).iterator():
        personal = Personal._base_manager.filter(
            clinica_id=paciente.clinica_id,
            ci=paciente.ci,
            usuario__isnull=False,
        ).first()
        if personal is None:
            continue

        # Nunca reasignar una cuenta que ya pertenece a otro expediente.
        if Paciente._base_manager.filter(usuario_id=personal.usuario_id).exists():
            continue

        rol_paciente = Rol._base_manager.filter(
            clinica_id=paciente.clinica_id,
            nombre="Paciente",
            estado=True,
        ).first()
        if rol_paciente is None:
            continue

        UsuarioRol._base_manager.get_or_create(
            usuario_id=personal.usuario_id,
            rol_id=rol_paciente.pk,
        )
        paciente.usuario_id = personal.usuario_id
        paciente.email = personal.usuario.email
        paciente.save(update_fields=["usuario", "email"])


class Migration(migrations.Migration):
    dependencies = [
        ("pacientes", "0002_initial"),
        ("personal", "0003_medico_especialidades"),
        ("seguridad", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(vincular_identidades_personal, migrations.RunPython.noop),
    ]
