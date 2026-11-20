"""Catálogo RBAC de manuales y diccionario data-guia-id para el Asistente Guía."""

from apps.core.seed_data import (
    ROL_ADMIN_CLINICA,
    ROL_CONDUCTOR,
    ROL_ENFERMERIA,
    ROL_MEDICO,
    ROL_PACIENTE,
    ROL_RECEPCIONISTA,
)


CATALOGO_PROCESOS = [
    {
        "id": "modulo_inicio",
        "roles": (
            ROL_ADMIN_CLINICA,
            ROL_MEDICO,
            ROL_RECEPCIONISTA,
            ROL_PACIENTE,
            ROL_ENFERMERIA,
            ROL_CONDUCTOR,
        ),
        "modulo": "Inicio",
        "ruta_objetivo": "/",
        "id_menu": "nav-inicio",
        "id_accion": None,
        "descripcion": "El módulo Inicio muestra el resumen principal y accesos rápidos a las funciones habilitadas para tu rol dentro de la clínica.",
        "pasos_base": [
            "Haz clic en 'Inicio' en el menú lateral para volver al panel principal.",
        ],
    },
    {
        "id": "modulo_mi_clinica",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi clínica",
        "ruta_objetivo": "/mi-clinica",
        "id_menu": "nav-mi-clinica",
        "id_accion": None,
        "descripcion": "El módulo Mi clínica permite consultar y administrar la información general de la clínica (nombre, dirección, teléfono, correo y datos institucionales).",
        "pasos_base": [
            "Ingresa a 'Mi clínica' desde el menú lateral para revisar o actualizar los datos de la clínica.",
        ],
    },
    {
        "id": "crear_cita",
        "roles": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "modulo": "Citas",
        "ruta_objetivo": "/citas",
        "id_menu": "nav-citas",
        "id_accion": "btn-nueva-cita",
        "descripcion": "Programar una nueva cita médica presencial o virtual (videollamada Daily.co) eligiendo paciente, especialidad, médico, fecha, horario disponible, modalidad y motivo.",
        "pasos_base": [
            "Ingresa al módulo Citas desde el menú lateral.",
            "Haz clic en el botón 'Nueva cita'.",
            "Selecciona paciente, especialidad, médico, fecha y un horario disponible.",
            "Elige la modalidad (Presencial o Virtual), escribe el motivo y guarda la cita.",
        ],
    },
    {
        "id": "gestionar_estados_cita",
        "roles": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "modulo": "Citas",
        "ruta_objetivo": "/citas",
        "id_menu": "nav-citas",
        "id_accion": "btn-fila-cita-confirmar",
        "descripcion": "Confirmar, reprogramar o cancelar citas existentes de la clínica, o filtrar citas por fecha y estado.",
        "pasos_base": [
            "Abre el módulo Citas desde el menú lateral.",
            "Ubica la cita en la tabla (puedes usar los filtros de fecha o estado).",
            "En la fila de la cita, usa los botones 'Confirmar', 'Reprogramar' o 'Cancelar'.",
        ],
    },
    {
        "id": "estudios_cita_admin",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Citas",
        "ruta_objetivo": "/citas",
        "id_menu": "nav-citas",
        "id_accion": "btn-fila-cita-estudios",
        "descripcion": "Subir, ver o eliminar estudios médicos (DICOM, imágenes PNG/JPG o PDF) asociados a una cita desde el rol Administrador de clínica. Solo se pueden agregar o eliminar estudios mientras la cita está PROGRAMADA o CONFIRMADA; si ya está ATENDIDA, CANCELADA o NO_ASISTIO únicamente se pueden consultar.",
        "pasos_base": [
            "Ingresa al módulo Citas desde el menú lateral.",
            "En la fila de la cita deseada, haz clic en el botón 'Estudios'.",
            "Selecciona el tipo de estudio, adjunta el archivo (.dcm, .png, .jpg o .pdf) y pulsa 'Subir estudio'.",
        ],
    },
    {
        "id": "registrar_paciente",
        "roles": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "modulo": "Pacientes",
        "ruta_objetivo": "/pacientes",
        "id_menu": "nav-pacientes",
        "id_accion": "btn-nuevo-paciente",
        "descripcion": "Registrar un nuevo paciente en la clínica (su historia clínica se crea automáticamente). Al guardar el paciente (o luego desde el botón 'Cuenta' de su fila, para Administrador de clínica), se ofrece la opción de crearle y vincularle una cuenta de usuario con el rol Paciente para acceder al portal.",
        "pasos_base": [
            "Ve al módulo Pacientes en el menú lateral.",
            "Presiona el botón 'Registrar paciente' y completa sus datos personales.",
            "Al guardar (o desde el botón 'Cuenta' en su fila), crea y vincula su usuario con el rol Paciente.",
        ],
    },
    {
        "id": "ver_historial_paciente",
        "roles": (ROL_MEDICO,),
        "modulo": "Pacientes",
        "ruta_objetivo": "/pacientes",
        "id_menu": "nav-pacientes",
        "id_accion": "btn-fila-paciente-historial",
        "descripcion": "Ver el historial de consultas atendidas, diagnósticos, recetas y estudios médicos de un paciente desde el listado de Pacientes.",
        "pasos_base": [
            "Abre el módulo Pacientes desde el menú lateral.",
            "Ubica al paciente en la tabla (puedes usar el buscador por nombre o CI).",
            "En la fila del paciente, haz clic en el botón 'Historial'.",
        ],
    },
    {
        "id": "ver_historia_clinica_paciente",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_RECEPCIONISTA),
        "modulo": "Pacientes",
        "ruta_objetivo": "/pacientes",
        "id_menu": "nav-pacientes",
        "id_accion": "btn-fila-paciente-ver",
        "descripcion": "Consultar el detalle de un paciente, revisar su historia clínica y gestionar sus enfermedades o alergias.",
        "pasos_base": [
            "Abre el módulo Pacientes desde el menú lateral.",
            "Ubica al paciente en la tabla.",
            "En la fila del paciente, haz clic en el botón 'Ver'.",
        ],
    },
    {
        "id": "ver_detalle_cita_agenda",
        "roles": (ROL_MEDICO,),
        "modulo": "Mi agenda",
        "ruta_objetivo": "/mi-agenda",
        "id_menu": "nav-mi-agenda",
        "id_accion": "btn-fila-agenda-ver",
        "descripcion": "Ver la información completa y detalle de una cita en Mi agenda (paciente, fecha, hora, modalidad, estado, motivo y enlaces) haciendo clic en el botón 'Ver' de la fila de la cita.",
        "pasos_base": [
            "En el módulo 'Mi agenda', ubica la cita usando los filtros de fecha o estado.",
            "En la fila de la cita, haz clic en el botón 'Ver' para abrir su detalle completo.",
        ],
    },
    {
        "id": "mi_agenda_telemedicina_consulta",
        "roles": (ROL_MEDICO,),
        "modulo": "Mi agenda",
        "ruta_objetivo": "/mi-agenda",
        "id_menu": "nav-mi-agenda",
        "id_accion": "btn-fila-agenda-sala",
        "descripcion": "Consultar las citas asignadas al médico por fecha y estado, ingresar a la sala virtual de videollamada (telemedicina) y revisar los estudios médicos de la cita.",
        "pasos_base": [
            "Entra a 'Mi agenda' desde el menú lateral.",
            "Selecciona la fecha y el estado para ubicar la cita.",
            "En la fila de la cita virtual, presiona 'Ingresar a la sala virtual'.",
        ],
    },
    {
        "id": "atender_cita_presencial",
        "roles": (ROL_MEDICO,),
        "modulo": "Mi agenda",
        "ruta_objetivo": "/mi-agenda",
        "id_menu": "nav-mi-agenda",
        "id_accion": "btn-fila-agenda-atender",
        "descripcion": "Atender una cita presencial confirmada en Mi agenda para registrar la consulta médica (motivo, observación, diagnóstico) y emitir recetas.",
        "pasos_base": [
            "Entra a 'Mi agenda' desde el menú lateral.",
            "Ubica la cita confirmada en la tabla.",
            "En la fila de la cita, presiona el botón 'Atender' y completa el formulario de consulta.",
        ],
    },
    {
        "id": "gestionar_usuarios",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Usuarios",
        "ruta_objetivo": "/usuarios",
        "id_menu": "nav-usuarios",
        "id_accion": "btn-fila-usuario-roles",
        "descripcion": "Administrar cuentas de usuario ya existentes (buscar, editar, activar/desactivar y modificar roles). Las cuentas de usuario nuevas NO se crean aquí: para crear un usuario de personal (como Médico o Recepcionista) primero créalo en 'Personal', y para crear un usuario con rol Paciente primero créalo en 'Pacientes'.",
        "pasos_base": [
            "Accede a Usuarios desde el menú lateral.",
            "Ubica la cuenta en la tabla (puedes usar el buscador).",
            "En la fila del usuario, haz clic en 'Roles' para asignar o modificar roles, o en 'Editar' / 'Desactivar'.",
        ],
    },
    {
        "id": "gestionar_roles",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Roles",
        "ruta_objetivo": "/roles",
        "id_menu": "nav-roles",
        "id_accion": "btn-nuevo-rol",
        "descripcion": "Consultar los roles base de la clínica, editar descripciones o crear roles personalizados.",
        "pasos_base": [
            "Abre el módulo Roles en el menú lateral.",
            "Usa el botón 'Nuevo rol' para crear un rol adicional o edita uno existente desde la tabla.",
        ],
    },
    {
        "id": "gestionar_personal",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Personal",
        "ruta_objetivo": "/personal",
        "id_menu": "nav-personal",
        "id_accion": "btn-nuevo-personal",
        "descripcion": "Registrar un nuevo miembro del personal y crearle su cuenta de usuario con su rol (por ejemplo, Médico, Recepcionista, Administrador de clínica o Enfermería). Al guardar el personal (o luego desde el botón 'Cuenta' de su fila) aparece la opción para crear y vincular su usuario.",
        "pasos_base": [
            "Entra al módulo Personal en el menú lateral.",
            "Haz clic en 'Registrar personal' y guarda sus datos.",
            "En el paso siguiente (o desde el botón 'Cuenta' de su fila), crea su cuenta de usuario y selecciona el rol correspondiente (por ejemplo, Médico).",
        ],
    },
    {
        "id": "vincular_cuenta_personal",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Personal",
        "ruta_objetivo": "/personal",
        "id_menu": "nav-personal",
        "id_accion": "btn-fila-personal-cuenta",
        "descripcion": "Crear o vincular la cuenta de usuario (eligiendo su rol, como Médico o Recepcionista) para un miembro del personal que ya está registrado en la tabla de Personal.",
        "pasos_base": [
            "Entra al módulo Personal en el menú lateral.",
            "Ubica al miembro del personal en la tabla.",
            "En la fila correspondiente, haz clic en el botón 'Cuenta' para crear o vincular su usuario y asignarle su rol.",
        ],
    },
    {
        "id": "gestionar_medicos",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Médicos",
        "ruta_objetivo": "/medicos",
        "id_menu": "nav-medicos",
        "id_accion": "btn-nuevo-medicos",
        "descripcion": "Registrar un médico asociando un registro de personal existente con su especialidad y número de colegiatura.",
        "pasos_base": [
            "Asegúrate de haber registrado primero a la persona en Personal y creado su cuenta con rol Médico.",
            "Ingresa a Médicos desde el menú lateral y haz clic en 'Registrar médico'.",
            "Elige el personal, su especialidad, número de colegiatura y guarda.",
        ],
    },
    {
        "id": "consultar_mi_registro_medico",
        "roles": (ROL_MEDICO,),
        "modulo": "Médicos",
        "ruta_objetivo": "/medicos",
        "id_menu": "nav-medicos",
        "id_accion": None,
        "descripcion": "Consultar tu registro profesional de médico y acceder a tus horarios.",
        "pasos_base": [
            "Ingresa a Médicos desde el menú lateral para revisar tu especialidad, colegiatura y estado.",
        ],
    },
    {
        "id": "gestionar_especialidades",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Especialidades",
        "ruta_objetivo": "/especialidades",
        "id_menu": "nav-especialidades",
        "id_accion": "btn-nuevo-especialidades",
        "descripcion": "Crear, editar o desactivar especialidades médicas disponibles en la clínica.",
        "pasos_base": [
            "Ve a Especialidades en el menú lateral.",
            "Haz clic en 'Nueva especialidad', ingresa nombre y descripción y guarda.",
        ],
    },
    {
        "id": "gestionar_horarios",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO),
        "modulo": "Horarios",
        "ruta_objetivo": "/horarios",
        "id_menu": "nav-horarios",
        "id_accion": "btn-nuevo-horarios",
        "descripcion": "El módulo Horarios sirve para configurar los días y franjas horarias de atención de cada médico. Estas franjas generan automáticamente los bloques disponibles de 30 minutos que luego permiten programar citas médicas.",
        "pasos_base": [
            "Abre el módulo Horarios desde el menú lateral.",
            "Presiona 'Crear horario', elige el día de la semana, hora de inicio y hora de fin, y guarda.",
        ],
    },
    {
        "id": "renovar_suscripcion",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi suscripción",
        "ruta_objetivo": "/suscripciones",
        "id_menu": "nav-suscripciones",
        "id_accion": "btn-suscripcion-renovar",
        "descripcion": "El módulo Mi suscripción sirve para revisar el estado y vigencia del plan actual de la clínica y extender su vigencia usando el botón 'Renovar'.",
        "pasos_base": [
            "En el módulo 'Mi suscripción', ubica el resumen de tu suscripción vigente.",
            "Haz clic en el botón 'Renovar' y confirma el nuevo período.",
        ],
    },
    {
        "id": "cambiar_plan_suscripcion",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi suscripción",
        "ruta_objetivo": "/suscripciones",
        "id_menu": "nav-suscripciones",
        "id_accion": "btn-suscripcion-cambiar-plan",
        "descripcion": "Cambiar el plan actual de la clínica por otro plan disponible desde el módulo Mi suscripción mediante el botón 'Cambiar plan'.",
        "pasos_base": [
            "En el módulo 'Mi suscripción', haz clic en el botón 'Cambiar plan'.",
            "Selecciona el nuevo plan deseado, revisa las fechas y confirma el cambio.",
        ],
    },
    {
        "id": "cancelar_suscripcion",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi suscripción",
        "ruta_objetivo": "/suscripciones",
        "id_menu": "nav-suscripciones",
        "id_accion": "btn-suscripcion-cancelar",
        "descripcion": "Cancelar la suscripción activa de la clínica desde el módulo Mi suscripción usando el botón 'Cancelar suscripción'.",
        "pasos_base": [
            "En el módulo 'Mi suscripción', haz clic en el botón 'Cancelar suscripción'.",
            "Confirma la cancelación en el cuadro de diálogo.",
        ],
    },
    {
        "id": "contratar_suscripcion",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi suscripción",
        "ruta_objetivo": "/suscripciones",
        "id_menu": "nav-suscripciones",
        "id_accion": "btn-suscripcion-contratar",
        "descripcion": "Contratar una nueva suscripción cuando la clínica no tiene un plan vigente o su suscripción venció, usando el botón 'Contratar plan' en Mi suscripción.",
        "pasos_base": [
            "En el módulo 'Mi suscripción', haz clic en el botón 'Contratar plan'.",
            "Elige el plan y las fechas de vigencia, y confirma la contratación.",
        ],
    },
    {
        "id": "consultar_historial_suscripciones",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Mi suscripción",
        "ruta_objetivo": "/suscripciones",
        "id_menu": "nav-suscripciones",
        "id_accion": "btn-fila-suscripcion-consultar",
        "descripcion": "Consultar el historial de suscripciones de la clínica, filtrar por estado registrado o ver el detalle de una suscripción con el botón 'Consultar' de la fila.",
        "pasos_base": [
            "En el módulo 'Mi suscripción', baja hasta la sección 'Historial de suscripciones'.",
            "Opcionalmente filtra por 'Estado registrado' y haz clic en 'Consultar' en la fila que deseas revisar.",
        ],
    },
    {
        "id": "modulo_planes_disponibles",
        "roles": (ROL_ADMIN_CLINICA,),
        "modulo": "Planes disponibles",
        "ruta_objetivo": "/planes",
        "id_menu": "nav-planes",
        "id_accion": None,
        "descripcion": "El módulo Planes disponibles muestra únicamente el catálogo comparativo de planes SaaS (precios, límites de usuarios, médicos y almacenamiento). Para contratar, renovar o cambiar de plan se usa el módulo Mi suscripción.",
        "pasos_base": [
            "Abre 'Planes disponibles' en el menú lateral para comparar los planes, límites y precios.",
        ],
    },
    {
        "id": "portal_paciente_resumen_pestanas",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": None,
        "descripcion": "El módulo Mi información contiene 4 pestañas: 'Mis datos' (datos personales registrados en solo lectura), 'Mi historia clínica' (enfermedades, antecedentes y alergias), 'Mis citas' (citas programadas, subir/ver estudios médicos e ingreso a sala virtual) y 'Mis consultas y recetas' (historial de consultas atendidas, diagnósticos, recetas médicas y estudios revisados).",
        "pasos_base": [],
    },
    {
        "id": "portal_paciente_datos",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": "tab-portal-datos",
        "descripcion": "La pestaña 'Mis datos' dentro de Mi información muestra tus datos personales registrados como paciente (CI, nombre, sexo, fecha de nacimiento, teléfono y correo) en modo de solo lectura.",
        "pasos_base": [
            "Abre 'Mi información' desde el menú lateral.",
            "Haz clic en la pestaña 'Mis datos' para consultar tu información personal registrada.",
        ],
    },
    {
        "id": "portal_paciente_historia",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": "tab-portal-historia",
        "descripcion": "La pestaña 'Mi historia clínica' dentro de Mi información permite consultar tus enfermedades, antecedentes y alergias registradas por el personal médico.",
        "pasos_base": [
            "Abre 'Mi información' desde el menú lateral.",
            "Haz clic en la pestaña 'Mi historia clínica' para revisar tus enfermedades y alergias registradas.",
        ],
    },
    {
        "id": "portal_paciente_citas_estudios",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": "btn-fila-portal-estudios",
        "descripcion": "La pestaña 'Mis citas' dentro de Mi información permite consultar tus citas y gestionar estudios médicos (DICOM, PNG/JPG o PDF) con el botón 'Estudios médicos'. Regla importante: solo se pueden subir o eliminar estudios cuando la cita está PROGRAMADA o CONFIRMADA; cuando la cita ya está ATENDIDA, CANCELADA o NO_ASISTIO no se pueden agregar ni eliminar más estudios, solo ver los ya cargados.",
        "pasos_base": [
            "Ingresa a 'Mi información' y selecciona la pestaña 'Mis citas'.",
            "En la tarjeta de la cita deseada, haz clic en el botón 'Estudios médicos' para subir o gestionar tus archivos.",
        ],
    },
    {
        "id": "portal_paciente_sala_virtual",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": "btn-fila-portal-sala",
        "descripcion": "Ingresar a la sala virtual de videollamada (telemedicina) de una cita virtual desde la pestaña 'Mis citas' en Mi información.",
        "pasos_base": [
            "Ingresa a 'Mi información' y selecciona la pestaña 'Mis citas'.",
            "En la tarjeta de tu cita virtual, haz clic en el botón 'Ingresar a la sala virtual'.",
        ],
    },
    {
        "id": "portal_paciente_consultas_recetas",
        "roles": (ROL_PACIENTE,),
        "modulo": "Mi información",
        "ruta_objetivo": "/mi-informacion",
        "id_menu": "nav-mi-informacion",
        "id_accion": "tab-portal-consultas",
        "descripcion": "La pestaña 'Mis consultas y recetas' dentro de Mi información permite ver tus recetas médicas emitidas, medicamentos recetados, historial de consultas atendidas (motivo, diagnóstico y observación) y estudios médicos revisados.",
        "pasos_base": [
            "Abre 'Mi información' y selecciona la pestaña 'Mis consultas y recetas'.",
            "En cada consulta podrás ver tus diagnósticos, abrir tus recetas médicas o pulsar 'Ver estudio' para abrir el visor en otra pestaña.",
        ],
    },
    {
        "id": "mi_cuenta_password",
        "roles": (
            ROL_ADMIN_CLINICA,
            ROL_MEDICO,
            ROL_RECEPCIONISTA,
            ROL_PACIENTE,
            ROL_ENFERMERIA,
            ROL_CONDUCTOR,
        ),
        "modulo": "Mi cuenta",
        "ruta_objetivo": "/cuenta",
        "id_menu": "nav-cuenta",
        "id_accion": "btn-cambiar-password",
        "descripcion": "Consultar los datos de la cuenta autenticada y cambiar la contraseña de acceso.",
        "pasos_base": [
            "Abre 'Mi cuenta' en el menú lateral.",
            "Completa el formulario de cambio de contraseña y confirma.",
        ],
    },
]


NOMBRES_VISUALES_UI = {
    # Menú lateral
    "nav-inicio": "opción 'Inicio' del menú lateral",
    "nav-cuenta": "opción 'Mi cuenta' del menú lateral",
    "nav-mi-informacion": "opción 'Mi información' del menú lateral",
    "nav-mi-clinica": "opción 'Mi clínica' del menú lateral",
    "nav-suscripciones": "opción 'Mi suscripción' del menú lateral",
    "nav-planes": "opción 'Planes disponibles' del menú lateral",
    "nav-usuarios": "opción 'Usuarios' del menú lateral",
    "nav-roles": "opción 'Roles' del menú lateral",
    "nav-personal": "opción 'Personal' del menú lateral",
    "nav-pacientes": "opción 'Pacientes' del menú lateral",
    "nav-citas": "opción 'Citas' del menú lateral",
    "nav-mi-agenda": "opción 'Mi agenda' del menú lateral",
    "nav-especialidades": "opción 'Especialidades' del menú lateral",
    "nav-medicos": "opción 'Médicos' del menú lateral",
    "nav-horarios": "opción 'Horarios' del menú lateral",
    # Botones y controles de acción
    "btn-nueva-cita": "botón 'Nueva cita'",
    "filtro-citas-estado": "selector de estado de citas",
    "btn-nuevo-paciente": "botón 'Registrar paciente'",
    "buscador-pacientes": "buscador de pacientes",
    "filtro-agenda-fecha": "selector de fecha en 'Mi agenda'",
    "buscador-usuarios": "buscador de usuarios",
    "btn-nuevo-rol": "botón 'Nuevo rol'",
    "btn-nuevo-personal": "botón 'Registrar personal'",
    "btn-nuevo-medicos": "botón 'Registrar médico'",
    "btn-nuevo-especialidades": "botón 'Nueva especialidad'",
    "btn-nuevo-horarios": "botón 'Crear horario'",
    "tab-portal-datos": "pestaña 'Mis datos'",
    "tab-portal-historia": "pestaña 'Mi historia clínica'",
    "tab-portal-citas": "pestaña 'Mis citas'",
    "tab-portal-consultas": "pestaña 'Mis consultas y recetas'",
    "btn-cambiar-password": "botón 'Actualizar contraseña'",
    # Acciones en filas de tablas y listas (se resalta el primer registro disponible)
    "btn-fila-paciente-ver": "botón 'Ver' de la fila del paciente",
    "btn-fila-paciente-cuenta": "botón 'Cuenta' de la fila del paciente",
    "btn-fila-paciente-historial": "botón 'Historial' de la fila del paciente",
    "btn-fila-paciente-editar": "botón 'Editar' de la fila del paciente",
    "btn-fila-cita-ver": "botón 'Ver' de la fila de la cita",
    "btn-fila-cita-estudios": "botón 'Estudios' de la fila de la cita",
    "btn-fila-cita-confirmar": "botón 'Confirmar' de la fila de la cita",
    "btn-fila-cita-reprogramar": "botón 'Reprogramar' de la fila de la cita",
    "btn-fila-cita-cancelar": "botón 'Cancelar' de la fila de la cita",
    "btn-fila-agenda-ver": "botón 'Ver' de la fila de la cita",
    "btn-fila-agenda-sala": "botón 'Ingresar a la sala virtual' de la fila de la cita",
    "btn-fila-agenda-atender": "botón 'Atender' de la fila de la cita",
    "btn-fila-agenda-consulta": "botón 'Ver consulta' de la fila de la cita",
    "btn-fila-usuario-editar": "botón 'Editar' de la fila del usuario",
    "btn-fila-usuario-roles": "botón 'Roles' de la fila del usuario",
    "btn-fila-personal-cuenta": "botón 'Cuenta' de la fila del personal",
    "btn-fila-portal-estudios": "botón 'Estudios médicos' en la pestaña 'Mis citas'",
    "btn-fila-portal-sala": "botón 'Ingresar a la sala virtual' en la pestaña 'Mis citas'",
    "btn-fila-portal-receta": "botón de receta de la consulta",
    "btn-fila-portal-ver-estudio": "botón 'Ver estudio' de la consulta",
    # Mi suscripción
    "btn-suscripcion-actualizar": "botón 'Actualizar estado'",
    "btn-suscripcion-contratar": "botón 'Contratar plan'",
    "btn-suscripcion-renovar": "botón 'Renovar'",
    "btn-suscripcion-cambiar-plan": "botón 'Cambiar plan'",
    "btn-suscripcion-cancelar": "botón 'Cancelar suscripción'",
    "filtro-suscripciones-estado": "selector 'Estado registrado'",
    "btn-fila-suscripcion-consultar": "botón 'Consultar' de la fila de la suscripción",
    # Visor de estudios médicos y Sala virtual de telemedicina
    "btn-visor-descargar": "botón 'Descargar'",
    "btn-visor-guardar-lectura": "botón 'Guardar lectura'",
    "btn-visor-contraste": "botón 'Contraste (W/L)'",
    "btn-visor-zoom": "botón 'Zoom / Mover'",
    "btn-visor-cortes": "botón 'Cortes (Scroll)'",
    "btn-visor-regla": "botón 'Regla / Medición'",
    "btn-visor-restablecer": "botón 'Restablecer'",
    "btn-visor-pantalla-completa": "botón 'Pantalla completa'",
    "btn-sala-cancelar": "botón 'Cancelar videollamada'",
    "btn-sala-abrir-visor": "botón 'Abrir visor' en estudios médicos de la cita",
    "btn-sala-agregar-medicamento": "botón 'Agregar medicamento'",
    "btn-sala-guardar-consulta": "botón 'Guardar consulta'",
    "btn-sala-agregar-receta": "botón 'Agregar receta'",
}


CATALOGO_VISOR_ESTUDIOS = [
    {
        "id": "visor_contraste",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-contraste",
        "descripcion": "La herramienta 'Contraste (W/L)' (Window/Level) sirve para ajustar el brillo y el contraste de una imagen médica DICOM: haz clic y arrastra el mouse horizontal o verticalmente sobre la imagen para resaltar tejidos, huesos o detalles clínicos.",
        "pasos_base": [
            "Haz clic en el botón 'Contraste (W/L)' en la barra superior oscura del visor.",
            "Mantén presionado el clic izquierdo sobre la imagen y arrastra en horizontal o vertical para ajustar brillo y contraste.",
        ],
    },
    {
        "id": "visor_zoom",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-zoom",
        "descripcion": "La herramienta 'Zoom / Mover' permite acercar o alejar el estudio médico con la rueda del mouse y desplazar la imagen haciendo clic y arrastrando para inspeccionar zonas específicas con detalle.",
        "pasos_base": [
            "Selecciona el botón 'Zoom / Mover' en la barra superior del visor.",
            "Usa la rueda del mouse para acercar o alejar, y arrastra la imagen para moverte por ella.",
        ],
    },
    {
        "id": "visor_cortes",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-cortes",
        "descripcion": "La herramienta 'Cortes (Scroll)' sirve en estudios DICOM multicorte (como tomografías o resonancias) para navegar entre los distintos cortes usando la rueda del mouse o la barra inferior (botones Anterior / Siguiente y deslizador). Si el archivo tiene un solo corte, el botón aparece deshabilitado.",
        "pasos_base": [
            "Si el estudio tiene múltiples cortes, haz clic en 'Cortes (Scroll)' en la barra superior.",
            "Gira la rueda del mouse sobre la imagen o usa la barra inferior (Anterior / Siguiente) para cambiar de corte.",
        ],
    },
    {
        "id": "visor_regla",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-regla",
        "descripcion": "La herramienta 'Regla / Medición' permite trazar líneas sobre una imagen DICOM para medir distancias o tamaños de hallazgos clínicos directamente en el estudio.",
        "pasos_base": [
            "Haz clic en el botón 'Regla / Medición' en la barra superior del visor.",
            "Haz clic y arrastra sobre la imagen desde el punto inicial hasta el punto final que deseas medir.",
        ],
    },
    {
        "id": "visor_restablecer",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-restablecer",
        "descripcion": "El botón 'Restablecer' devuelve la imagen médica a su zoom, posición y contraste originales sin modificar ni borrar el archivo.",
        "pasos_base": [
            "Haz clic en el botón 'Restablecer' en la barra superior oscura del visor para volver a la vista inicial.",
        ],
    },
    {
        "id": "visor_pantalla_completa",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-pantalla-completa",
        "descripcion": "El botón 'Pantalla completa' amplía todo el contenedor del visor (imagen y barra de herramientas) para diagnosticar con mayor comodidad sin perder acceso a Contraste, Zoom, Regla o Cortes; puedes salir pulsando el mismo botón o la tecla Esc.",
        "pasos_base": [
            "Haz clic en el botón 'Pantalla completa' al extremo derecho de la barra superior del visor.",
            "Para salir, presiona 'Salir de pantalla completa' o la tecla Esc.",
        ],
    },
    {
        "id": "visor_descargar",
        "roles": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-descargar",
        "descripcion": "El botón 'Descargar' en la cabecera superior permite guardar una copia del archivo original del estudio médico (.dcm, .png, .jpg o .pdf) en tu dispositivo.",
        "pasos_base": [
            "Haz clic en el botón 'Descargar' en la esquina superior derecha del visor.",
        ],
    },
    {
        "id": "visor_estudios_guardar_lectura",
        "roles": (ROL_MEDICO,),
        "modulo": "Visor de estudios médicos",
        "ruta_objetivo": "/estudios",
        "id_menu": None,
        "id_accion": "btn-visor-guardar-lectura",
        "descripcion": "El panel 'Lectura e informe médico' a la derecha del visor permite al médico escribir sus hallazgos, interpretación y conclusiones clínicas sobre el estudio y guardarlos con el botón 'Guardar lectura'.",
        "pasos_base": [
            "Escribe tus hallazgos e interpretación en el campo 'Observación / Lectura' del panel derecho.",
            "Haz clic en el botón 'Guardar lectura' para registrar el informe del estudio.",
        ],
    },
]


CATALOGO_SALA_VIRTUAL = [
    {
        "id": "sala_virtual_videollamada",
        "roles": (ROL_MEDICO, ROL_PACIENTE),
        "modulo": "Sala virtual de telemedicina",
        "ruta_objetivo": "/sala-virtual",
        "id_menu": None,
        "id_accion": "btn-sala-cancelar",
        "descripcion": "La videollamada de la sala virtual conecta en vivo al médico y al paciente mediante Daily.co. Incluye controles de cámara, micrófono y pantalla completa en la parte inferior, y el botón 'Cancelar videollamada' en la cabecera para salir.",
        "pasos_base": [
            "Permite el acceso a cámara y micrófono en el navegador.",
            "Usa los controles inferiores de la videollamada para activar o silenciar cámara y micrófono.",
            "Cuando finalices, pulsa 'Cancelar videollamada' en la cabecera superior para cerrar la sala.",
        ],
    },
    {
        "id": "sala_virtual_estudios",
        "roles": (ROL_MEDICO,),
        "modulo": "Sala virtual de telemedicina",
        "ruta_objetivo": "/sala-virtual",
        "id_menu": None,
        "id_accion": "btn-sala-abrir-visor",
        "descripcion": "La sección 'Estudios médicos de esta cita' en el panel derecho muestra los estudios subidos por el paciente o administrador para esta cita y permite abrir cualquiera en el visor médico haciendo clic en 'Abrir visor'.",
        "pasos_base": [
            "En el panel derecho de la sala virtual, ubica la sección 'Estudios médicos de esta cita'.",
            "Haz clic en 'Abrir visor' en el estudio que deseas revisar (se abrirá en otra pestaña).",
        ],
    },
    {
        "id": "sala_virtual_medicamentos_receta",
        "roles": (ROL_MEDICO,),
        "modulo": "Sala virtual de telemedicina",
        "ruta_objetivo": "/sala-virtual",
        "id_menu": None,
        "id_accion": "btn-sala-agregar-medicamento",
        "descripcion": "Dentro del panel de consulta de la sala virtual puedes emitir una receta médica opcional pulsando 'Agregar medicamento' para indicar nombre, dosis, frecuencia, duración e indicaciones generales (o 'Agregar receta' si la consulta ya fue guardada).",
        "pasos_base": [
            "En el panel derecho, haz clic en el botón 'Agregar medicamento' dentro de 'Receta médica (opcional)'.",
            "Completa nombre, dosis, frecuencia, duración e indicaciones generales y luego guarda la consulta.",
        ],
    },
    {
        "id": "sala_virtual_consulta_receta",
        "roles": (ROL_MEDICO,),
        "modulo": "Sala virtual de telemedicina",
        "ruta_objetivo": "/sala-virtual",
        "id_menu": None,
        "id_accion": "btn-sala-guardar-consulta",
        "descripcion": "El formulario 'Consulta y recetas' en el panel derecho permite registrar el motivo, observaciones y diagnóstico de la consulta virtual. Al pulsar 'Guardar consulta', la cita pasa a atendida y los estudios médicos de la cita se vinculan automáticamente a la consulta.",
        "pasos_base": [
            "Completa 'Motivo de consulta', 'Observaciones' y 'Diagnóstico' en el panel derecho.",
            "Opcionalmente agrega medicamentos en la sección de receta médica.",
            "Haz clic en el botón 'Guardar consulta'.",
        ],
    },
]


# Reglas determinísticas de permiso por intención para bloquear al instante consultas
# sobre procesos que no corresponden al rol del usuario (sin riesgo de alucinación).
REGLAS_PERMISO_PROCESOS = [
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "accion": "crear o programar citas médicas",
        "patrones": (
            r"\b(cre(ar|o)|nueva|program(ar|o)|agend(ar|o)|registr(ar|o))\b.{0,25}\bcitas?\b",
            r"\bcitas?\b.{0,20}\b(nueva|cre(ar|o)|program(ar|o)|agend(ar|o))\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "accion": "confirmar, reprogramar o cancelar citas",
        "patrones": (
            r"\b(confirm(ar|o)|reprogram(ar|o)|cancel(ar|o))\b.{0,25}\bcitas?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_RECEPCIONISTA),
        "accion": "registrar nuevos pacientes",
        "patrones": (
            r"\b(registr(ar|o)|cre(ar|o)|nuevo|agreg(ar|o))\b.{0,20}\bpacientes?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_MEDICO, ROL_RECEPCIONISTA),
        "accion": "consultar el módulo de pacientes",
        "patrones": (
            r"\b(modulo|listado|tabla)\b.{0,15}\bpacientes?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_MEDICO,),
        "accion": "ver el historial de consultas de otros pacientes",
        "patrones": (
            r"\bhistorial\b.{0,20}\b(un|del|de)\s+paciente\b",
        ),
    },
    {
        "roles_permitidos": (ROL_MEDICO,),
        "accion": "atender citas o acceder a Mi agenda",
        "patrones": (
            r"\b(atend(er|o)\s+(una\s+)?cita|mi\s+agenda)\b",
        ),
    },
    {
        "roles_permitidos": (ROL_MEDICO,),
        "accion": "registrar consultas médicas o emitir recetas",
        "patrones": (
            r"\b(guard(ar|o)|registr(ar|o)|cre(ar|o))\b.{0,20}\bconsultas?\b",
            r"\b(emit(ir|o)|cre(ar|o)|agreg(ar|o))\b.{0,20}\b(recetas?|medicamentos?)\b",
        ),
    },
    {
        "roles_permitidos": (ROL_MEDICO,),
        "accion": "guardar la lectura o informe médico de un estudio",
        "patrones": (
            r"\b(guard(ar|o)|registr(ar|o)|escrib(ir|o))\b.{0,20}\b(lectura|informe\s+medico)\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_PACIENTE),
        "accion": "subir o eliminar estudios médicos en una cita",
        "patrones": (
            r"\b(sub(ir|o)|carg(ar|o)|agreg(ar|o)|elimin(ar|o)|borr(ar|o))\b.{0,25}\bestudios?\s+medicos?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "administrar usuarios o asignar roles",
        "patrones": (
            r"\b(administr(ar|o)|gestion(ar|o)|desactiv(ar|o)|reactiv(ar|o)|edit(ar|o))\b.{0,20}\busuarios?\b",
            r"\basign(ar|o)\b.{0,15}\brol(es)?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "crear o gestionar roles",
        "patrones": (
            r"\b(cre(ar|o)|nuevo|edit(ar|o)|gestion(ar|o))\b.{0,20}\brol(es)?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "registrar o administrar personal",
        "patrones": (
            r"\b(registr(ar|o)|cre(ar|o)|nuevo|gestion(ar|o)|vincul(ar|o))\b.{0,20}\bpersonal\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "registrar nuevos médicos",
        "patrones": (
            r"\b(registr(ar|o)|cre(ar|o)|nuevo|dar\s+de\s+alta)\b.{0,20}\bmedicos?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "crear o gestionar especialidades",
        "patrones": (
            r"\b(cre(ar|o)|nueva|edit(ar|o)|desactiv(ar|o)|gestion(ar|o))\b.{0,20}\bespecialidad(es)?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA, ROL_MEDICO),
        "accion": "configurar horarios de atención",
        "patrones": (
            r"\b(cre(ar|o)|configur(ar|o)|edit(ar|o)|gestion(ar|o)|modulo\s+de)\b.{0,20}\bhorarios?\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "administrar la suscripción o cambiar el plan de la clínica",
        "patrones": (
            r"\b(mi\s+suscripcion|(renov(ar|o)|renuevo)\s+(la\s+|mi\s+)?suscripcion|cancel(ar|o)\s+(la\s+|mi\s+)?suscripcion|contrat(ar|o)\s+(un\s+)?plan|cambi(ar|o)\s+(de\s+)?plan|planes\s+disponibles)\b",
        ),
    },
    {
        "roles_permitidos": (ROL_ADMIN_CLINICA,),
        "accion": "administrar la información general de Mi clínica",
        "patrones": (
            r"\bmi\s+clinica\b",
        ),
    },
]


def filtrar_catalogo_por_roles(roles_usuario, ruta_actual="/"):
    """Devuelve únicamente los procesos autorizados para los roles del usuario y el contexto actual."""

    roles_set = set(roles_usuario)
    ruta = (ruta_actual or "/").strip()
    if ruta.startswith("/estudios"):
        fuente = CATALOGO_VISOR_ESTUDIOS
    elif ruta.startswith("/sala-virtual"):
        fuente = CATALOGO_SALA_VIRTUAL
    else:
        fuente = CATALOGO_PROCESOS

    return [
        proceso
        for proceso in fuente
        if roles_set.intersection(proceso["roles"])
    ]
