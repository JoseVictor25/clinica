"""Datos base compartidos por la semilla y la provisión de clínicas."""

from decimal import Decimal

ROL_ADMIN_CLINICA = "Administrador de clínica"
ROL_RECEPCIONISTA = "Recepcionista"
ROL_MEDICO = "Médico"
ROL_CONDUCTOR = "Conductor"
ROL_PACIENTE = "Paciente"

ROLES_BASE = [
    (
        ROL_ADMIN_CLINICA,
        "Gestiona usuarios, personal y configuración de la clínica.",
    ),
    (ROL_RECEPCIONISTA, "Gestiona citas y atención al paciente."),
    (ROL_MEDICO, "Atiende consultas y registra historias clínicas."),
    (ROL_CONDUCTOR, "Realiza traslados en ambulancia."),
    (ROL_PACIENTE, "Accede a su información clínica."),
]

ESPECIALIDADES_BASE = [
    "Medicina General",
    "Pediatría",
    "Cardiología",
    "Ginecología",
    "Traumatología",
    "Dermatología",
    "Neurología",
    "Oftalmología",
]

PLANES_BASE = [
    ("Básico", Decimal("29.00"), 5, "Plan básico para clínicas pequeñas."),
    ("Estándar", Decimal("59.00"), 15, "Plan para clínicas en crecimiento."),
    ("Premium", Decimal("99.00"), 50, "Plan para clínicas grandes."),
]

ROLES_BASE_NOMBRES = {nombre for nombre, _ in ROLES_BASE}
