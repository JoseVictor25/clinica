"""
Comando idempotente de datos semilla.

Uso:
    python manage.py cargar_semilla

Carga:
  - Planes de suscripción.
  - Roles base por cada clínica.
  - Especialidades base por cada clínica.
  - Usuario administrador del sistema (sin clínica), leyendo credenciales del .env.

Se puede ejecutar varias veces sin duplicar registros.
"""

from decimal import Decimal

from decouple import UndefinedValueError, config
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clinicas.models import Clinica, PlanSuscripcion
from apps.personal.models import Especialidad
from apps.seguridad.models import Rol, Usuario

PLANES = [
    ("Básico", Decimal("29.00"), 5, "Plan básico para clínicas pequeñas."),
    ("Estándar", Decimal("59.00"), 15, "Plan para clínicas en crecimiento."),
    ("Premium", Decimal("99.00"), 50, "Plan para clínicas grandes."),
]

ROLES = [
    ("Administrador de clínica", "Gestiona usuarios, personal y configuración de la clínica."),
    ("Recepcionista", "Gestiona citas y atención al paciente."),
    ("Médico", "Atiende consultas y registra historias clínicas."),
    ("Conductor", "Realiza traslados en ambulancia."),
    ("Paciente", "Accede a su información clínica."),
]

ESPECIALIDADES = [
    "Medicina General",
    "Pediatría",
    "Cardiología",
    "Ginecología",
    "Traumatología",
    "Dermatología",
    "Neurología",
    "Oftalmología",
]


def _env(nombre, default=None, cast=str):
    try:
        return config(nombre, default=default, cast=cast)
    except (UndefinedValueError, ValueError):
        return default


class Command(BaseCommand):
    help = "Carga planes, roles, especialidades y el administrador del sistema."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Cargando datos semilla...")

        planes_creados = self._cargar_planes()
        clinicas = self._obtener_clinicas()
        roles_creados = self._cargar_roles(clinicas)
        especialidades_creadas = self._cargar_especialidades(clinicas)
        admin_creado = self._cargar_admin_sistema()

        self.stdout.write(
            self.style.SUCCESS(
                "Semilla completada: "
                f"{planes_creados} planes nuevos, "
                f"{roles_creados} roles nuevos, "
                f"{especialidades_creadas} especialidades nuevas, "
                f"administrador {'creado' if admin_creado else 'actualizado'}."
            )
        )

    def _cargar_planes(self):
        creados = 0
        for nombre, precio, max_usuarios, descripcion in PLANES:
            _, creado = PlanSuscripcion.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "precio": precio,
                    "max_usuarios": max_usuarios,
                    "descripcion": descripcion,
                },
            )
            creados += int(creado)
        return creados

    def _obtener_clinicas(self):
        clinicas = list(Clinica.objects.all())
        if clinicas:
            return clinicas

        crear_demo = _env("SEED_CREAR_CLINICA_DEMO", default=True, cast=bool)
        if not crear_demo:
            self.stdout.write(
                self.style.WARNING(
                    "No hay clínicas registradas y SEED_CREAR_CLINICA_DEMO=False. "
                    "No se crearán roles ni especialidades."
                )
            )
            return []

        nit = _env("SEED_CLINICA_DEMO_NIT", default="DEMO-0001")
        nombre = _env("SEED_CLINICA_DEMO_NOMBRE", default="Clinica Demo")
        clinica, creada = Clinica.objects.get_or_create(
            nit=nit,
            defaults={
                "nombre": nombre,
                "direccion": "Av. Demo 123",
                "telefono": "0000000",
                "email": "demo@clinicas.local",
            },
        )
        if creada:
            self.stdout.write(f"  Clínica demo creada: {clinica.nombre}")
        return [clinica]

    def _cargar_roles(self, clinicas):
        creados = 0
        for clinica in clinicas:
            for nombre, descripcion in ROLES:
                _, creado = Rol.all_objects.get_or_create(
                    clinica=clinica,
                    nombre=nombre,
                    defaults={"descripcion": descripcion},
                )
                creados += int(creado)
        return creados

    def _cargar_especialidades(self, clinicas):
        creadas = 0
        for clinica in clinicas:
            for nombre in ESPECIALIDADES:
                _, creada = Especialidad.all_objects.get_or_create(
                    clinica=clinica,
                    nombre=nombre,
                    defaults={"descripcion": f"Especialidad de {nombre}."},
                )
                creadas += int(creada)
        return creadas

    def _cargar_admin_sistema(self):
        username = _env("ADMIN_SISTEMA_USERNAME")
        email = _env("ADMIN_SISTEMA_EMAIL")
        password = _env("ADMIN_SISTEMA_PASSWORD")

        if not username or not email:
            raise CommandError(
                "Faltan ADMIN_SISTEMA_USERNAME y/o ADMIN_SISTEMA_EMAIL en el .env."
            )

        admin = Usuario.all_objects.filter(username=username).first()
        if admin:
            admin.email = email
            admin.clinica = None
            admin.estado = True
            admin.is_staff = True
            admin.is_superuser = True
            admin.save(
                update_fields=[
                    "email",
                    "clinica",
                    "estado",
                    "is_staff",
                    "is_superuser",
                ]
            )
            return False

        if not password:
            raise CommandError(
                "Falta ADMIN_SISTEMA_PASSWORD en el .env para crear el administrador."
            )

        Usuario.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        return True
