# PROMPT PARA AGENTE DE IA – SPRINT 1 (SOLO BACKEND)

## SaaS Multitenant de Clínicas · Python + Django

---

## 1. ROL

Actúa como **desarrollador backend senior en Python/Django** con experiencia en arquitecturas SaaS multitenant, Django REST Framework y autenticación con JWT.

Vas a desarrollar el **Sprint 1** del backend de un SaaS de gestión de clínicas. El proyecto es un monorepo con dos carpetas: `backend/` (Django) y `frontend/` (React). **En este sprint solo trabajas en `backend/`. No toques `frontend/`.**

---

## 2. FORMA DE TRABAJO (OBLIGATORIA)

Trabajarás en **3 fases estrictas**. No pases a la siguiente fase sin cumplir la condición indicada.

### FASE 1 – PROPUESTA (sin ejecutar nada)

1. Explora el repositorio en modo **solo lectura** (lista carpetas, lee archivos existentes, revisa `requirements.txt`, `settings`, etc.).
2. **NO crees, edites, borres ni ejecutes** nada que modifique el proyecto (nada de `pip install`, `migrate`, `startapp`, creación de archivos, commits, etc.).
3. Entrega una **propuesta de trabajo** en el chat con este contenido:
   - **a)** Estado actual del proyecto (qué ya existe y qué falta).
   - **b)** Arquitectura propuesta: apps de Django, modelos con sus campos y relaciones, estrategia multitenant, estrategia de autenticación/autorización.
   - **c)** Lista de endpoints que se van a crear (método + ruta + qué hace + qué roles pueden usarlo).
   - **d)** Plan de trabajo ordenado por pasos, mapeado a las historias S1-01 … S1-14.
   - **e)** Dependencias/librerías a instalar (con justificación).
   - **f)** Plan de pruebas.
   - **g)** Supuestos que estás haciendo, dudas y decisiones que necesitan mi confirmación.
4. **DETENTE** y espera. Termina tu mensaje con: *"Esperando tu aprobación para comenzar."*

> **Condición para pasar a la Fase 2:** que yo escriba explícitamente **"APROBADO"** (o "puedes comenzar"). Si pido cambios a la propuesta, ajústala y vuelve a presentarla; sigue sin ejecutar nada hasta recibir la aprobación.

### FASE 2 – EJECUCIÓN

- Implementa **exactamente lo aprobado**, en el orden del plan.
- Si surge algo no contemplado (un cambio de diseño, una librería extra, un conflicto), **detente y pregúntame** antes de improvisar.
- Haz cambios pequeños y verificables; ejecuta las pruebas a medida que avanzas.
- No implementes nada fuera del alcance del Sprint 1 (ver sección 5).

### FASE 3 – INFORME FINAL

Al terminar, genera el archivo `backend/INFORME_SPRINT1.md` **y** muestra un resumen en el chat con:

1. **Resumen ejecutivo** (qué se logró).
2. **Estado por historia de usuario** (S1-01 … S1-14): ✅ completa / ⚠️ parcial / ❌ pendiente, con una línea de explicación.
3. **Estructura final** de carpetas/apps creadas.
4. **Modelos creados** (campos, relaciones, restricciones).
5. **Endpoints implementados** (tabla: método, ruta, descripción, roles permitidos).
6. **Decisiones técnicas** tomadas y su justificación.
7. **Librerías instaladas** (versiones).
8. **Pruebas**: qué se probó, cuántas pruebas hay y el resultado de su ejecución.
9. **Cómo ejecutar el proyecto** (instalación, migraciones, datos semilla, correr servidor y pruebas).
10. **Problemas encontrados, deuda técnica y recomendaciones** para el Sprint 2.

---

## 3. CONTEXTO TÉCNICO

### Stack

- Python 3.11+ · Django 5.x · Django REST Framework
- Autenticación: JWT (`djangorestframework-simplejwt`)
- Base de datos: **PostgreSQL** (configurable por variables de entorno con `python-decouple` o `django-environ`)
- Documentación de API: `drf-spectacular` (Swagger/OpenAPI)
- CORS: `django-cors-headers` (para el futuro frontend React)
- Pruebas: `pytest` + `pytest-django` (o el test runner de Django; propón y justifica)

### Estrategia multitenant

**Base de datos compartida y esquema compartido**, con aislamiento por columna `clinica` (FK → `Clinica`, equivale a `clinica_id`).

- Toda entidad que pertenezca a una clínica lleva FK a `Clinica`.
- Debe existir un **mecanismo centralizado de aislamiento** (middleware y/o mixin de ViewSet + manager de modelo) que filtre automáticamente por la clínica del usuario autenticado, de modo que **ningún usuario pueda leer o modificar datos de otra clínica**.
- Al crear registros, la clínica se asigna **desde el usuario autenticado**, nunca desde el body de la petición.
- El **administrador del sistema** (dueño de la plataforma) no pertenece a ninguna clínica y puede gestionar clínicas y planes.

### Estructura sugerida del backend (puedes proponer ajustes)

```
backend/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                 # settings (base/dev/prod), urls, wsgi, asgi
├── apps/
│   ├── core/               # utilidades compartidas: modelos base, middleware tenant, permisos, paginación, excepciones
│   ├── clinicas/           # Clinica, PlanSuscripcion, Suscripcion
│   ├── seguridad/          # Usuario, Roles, UsuarioRol, auth (login/logout), permisos por rol
│   └── personal/           # Personal, Especialidad, Medico, HorarioAtencion
└── tests/
```

---

## 4. ALCANCE DEL SPRINT 1

**Objetivo:** permitir registrar una clínica, suscribirla a un plan, autenticar usuarios con roles y gestionar personal médico.

### Historias de usuario

| ID | Historia | Entidades | Prior. | Pts |
|---|---|---|---|---|
| S1-01 | Como administrador del sistema, registro una clínica (tenant) | CLINICA | A | 5 |
| S1-02 | Como administrador del sistema, gestiono planes de suscripción (CRUD) | PLAN_SUSCRIPCION | A | 3 |
| S1-03 | Como clínica, contrato un plan y se crea mi suscripción | SUSCRIPCION | A | 5 |
| S1-04 | Como sistema, valido vigencia de suscripción y límite `max_usuarios` | SUSCRIPCION, PLAN_SUSCRIPCION | M | 5 |
| S1-05 | Como usuario, inicio y cierro sesión (autenticación con `password_hash`) | USUARIO | A | 5 |
| S1-06 | Como administrador de clínica, gestiono usuarios de mi clínica (CRUD) | USUARIO | A | 5 |
| S1-07 | Como administrador de clínica, defino roles y los asigno a usuarios | ROLES, USUARIO_ROL | A | 5 |
| S1-08 | Como sistema, restrinjo accesos según rol (autorización) | ROLES, USUARIO_ROL | A | 5 |
| S1-09 | Como administrador de clínica, registro y gestiono personal | PERSONAL | A | 5 |
| S1-10 | Como administrador de clínica, vinculo un usuario con su personal | USUARIO, PERSONAL | M | 2 |
| S1-11 | Como administrador de clínica, gestiono especialidades | ESPECIALIDAD | M | 2 |
| S1-12 | Como administrador de clínica, registro médicos con especialidad y colegiatura | MEDICO, ESPECIALIDAD | A | 5 |
| S1-13 | Como médico, configuro mis horarios de atención | HORARIO_ATENCION | M | 3 |
| S1-14 | Pruebas de aislamiento entre clínicas (tenant A no ve datos de tenant B) | Todas | A | 3 |

### Trabajo base de Sprint 0 que el backend necesita

Si no existe aún, inclúyelo en tu propuesta como paso previo: configuración del proyecto Django, conexión a la BD, modelos/migraciones de las entidades de este sprint, middleware de aislamiento por clínica y **datos semilla** (planes de suscripción, roles base, especialidades).

### Modelo de datos (según el diagrama de clases)

> Los nombres de campos vienen del diagrama. Usa convenciones de Python/Django (`snake_case` en campos, `PascalCase` en modelos) y propón los tipos de dato.

**Clinica**: id, nombre, direccion, telefono, email, nit (único), estado.
**Plan_Suscripcion**: id, nombre, precio, max_usuarios, descripcion.
**Suscripcion**: id, fecha_inicio, fecha_fin, estado. Relaciones: pertenece a una Clinica y a un Plan (una clínica puede tener varias suscripciones a lo largo del tiempo; solo una vigente a la vez).
**Usuario**: id, username, password (almacenado como hash), email, fecha_creacion, estado. Pertenece a una Clinica (el administrador del sistema no tiene clínica).
**Roles**: id, nombre, descripcion. Definidos por Clinica.
**Usuario_Rol**: id, fecha_asignacion. Relaciona Usuario ↔ Roles (un usuario puede tener varios roles; no se permiten asignaciones duplicadas).
**Personal**: ci, nombre, apellido, telefono, cargo, fecha_ingreso, estado. Pertenece a una Clinica.
**Especialidad**: id, nombre, descripcion.
**Medico**: id, numero_colegiatura, estado. Especialización de Personal (relación 1 a 0..1) y asociado a **una sola** Especialidad.
**Horario_Atencion**: id, dia_semana, hora_inicio, hora_fin. Un Médico tiene 1..* horarios.

Relaciones adicionales requeridas por las historias:
- **S1-10:** vínculo opcional uno a uno entre `Usuario` y `Personal`.

> ⚠️ **Observaciones sobre el diagrama** que debes confirmar conmigo en tu propuesta:
> 1. El atributo `Mas_Usuarios` de `Plan_Suscripcion` es un error de escritura; debe ser **`max_usuarios`**.
> 2. El diagrama guarda `Password`; en el código debe almacenarse **siempre hasheado** (`password_hash` / sistema de hashing de Django), nunca en texto plano.
> 3. Decide y justifica si `Especialidad` es global o por clínica (S1-11 indica que cada administrador de clínica las gestiona).
> 4. Las entidades de Paciente, Cita, Consulta, Receta, Ambulancia, etc. **no** se implementan en este sprint, pero el diseño no debe impedir agregarlas después.

### Reglas de negocio que deben cumplirse

- **RN-01:** Todo dato pertenece a una clínica; ningún usuario accede a datos de otra clínica.
- **RN-02:** Sin suscripción vigente no se permite iniciar sesión en esa clínica.
- **RN-03:** Una clínica no puede superar el `max_usuarios` de su plan.
- Un NIT de clínica no puede repetirse. La colegiatura de un médico no puede repetirse.
- Un rol no puede asignarse dos veces al mismo usuario.
- Un usuario/rol/personal/médico solo puede gestionarse dentro de su propia clínica.

### Casos de uso relacionados

CU-01 Registrar clínica · CU-02 Gestionar planes · CU-03 Contratar suscripción · CU-04 Validar vigencia de suscripción · CU-05 Iniciar sesión · CU-06 Cerrar sesión · CU-07 Gestionar usuarios · CU-08 Gestionar roles · CU-09 Asignar roles a usuario · CU-10 Gestionar personal · CU-11 Gestionar especialidades · CU-12 Gestionar médicos · CU-13 Gestionar horarios de atención.

**Flujo clave – Iniciar sesión (CU-05):**
1. El usuario envía username y contraseña.
2. El sistema compara contra el hash.
3. El sistema valida que la clínica tenga suscripción vigente (si no: bloquea el acceso e informa).
4. Carga roles y permisos y devuelve los tokens con el contexto de la clínica.

**Flujo clave – Contratar suscripción (CU-03):** si ya existe una suscripción vigente, el sistema ofrece renovar o cambiar de plan en lugar de duplicarla.

---

## 5. FUERA DE ALCANCE (NO HACER)

- Nada en `frontend/`.
- Entidades de Sprint 2 en adelante: Paciente, Historia Clínica, Enfermedad, Alergia, Cita, Consulta, Receta, Medicamento_Recetado.
- Ambulancias, Equipamiento, Traslado y Licencia_Conducir.
- Reportes y notificaciones.
- Despliegue, Docker o CI/CD (salvo que yo lo pida).

---

## 6. REQUISITOS DE CALIDAD

- **Código limpio**: separación en capas (modelos, serializers, vistas/viewsets, servicios para la lógica de negocio, permisos).
- **Validaciones** en serializers y/o servicios con mensajes de error claros **en español**.
- **Seguridad**: contraseñas hasheadas, secretos en variables de entorno (nunca en el código), permisos por defecto restrictivos (`IsAuthenticated`), sin exponer el hash en ninguna respuesta.
- **Autorización por rol**: permisos reutilizables (por ejemplo `IsAdminSistema`, `IsAdminClinica`, `IsMedico`) aplicados a cada endpoint.
- **API REST** consistente: paginación, filtros básicos, códigos HTTP correctos, rutas versionadas (`/api/v1/...`).
- **Documentación**: Swagger/OpenAPI accesible y `README` del backend con instrucciones de instalación.
- **Pruebas** (mínimo):
  - Autenticación (login correcto, credenciales inválidas, suscripción vencida).
  - Reglas RN-02 y RN-03.
  - Autorización por rol (cada rol solo accede a lo permitido).
  - **Aislamiento multitenant (S1-14):** el usuario de la clínica A no puede listar, ver, editar ni eliminar datos de la clínica B (probar para cada entidad con clínica).
- Un `.env.example` con todas las variables necesarias y un `.gitignore` correcto.
- Comandos de gestión o *fixtures* para cargar los datos semilla.

---

## 7. INSTRUCCIÓN INICIAL

Comienza ahora con la **FASE 1**: explora el repositorio en modo solo lectura y entrégame tu **propuesta**. **No ejecutes ni modifiques nada** hasta que yo escriba **"APROBADO"**.
