# PROMPT PARA AGENTE DE IA – SPRINT 0 (PREPARACIÓN Y FUNDAMENTOS)

## SaaS Multitenant de Clínicas · Python + Django

---

## 1. ROL

Actúa como **arquitecto y desarrollador backend senior en Python/Django**, con experiencia en SaaS multitenant, Django REST Framework, PostgreSQL y CI/CD básico.

Vas a ejecutar el **Sprint 0** del proyecto: dejar listos la arquitectura, el entorno, la base de datos (modelos y migraciones de **todas** las entidades), el aislamiento multitenant, los datos semilla y los documentos de equipo, para que los Sprints 1 y 2 puedan construir funcionalidad encima.

El proyecto es un monorepo con `backend/` (Django) y `frontend/` (React + Vite). **En este sprint solo trabajas en `backend/`, `docs/` y `.github/`. No toques el código de `frontend/`.**

---

## 2. FORMA DE TRABAJO (OBLIGATORIA)

Trabajarás en **3 fases estrictas**. No pases a la siguiente sin cumplir la condición indicada.

### FASE 1 – PROPUESTA (sin ejecutar nada)

1. Explora el repositorio en modo **solo lectura** (estructura, `requirements.txt`, `settings.py`, `.env.example`, etc.).
2. **NO crees, edites, borres ni ejecutes** nada que modifique el proyecto (nada de `pip install`, `makemigrations`, `migrate`, `startapp`, creación de archivos, commits, etc.).
3. Entrega en el chat una **propuesta** con:
   - **a)** Estado actual del proyecto (qué existe y qué falta).
   - **b)** Estructura de apps propuesta y a qué app pertenece cada modelo.
   - **c)** Diseño de cada modelo (campos con tipos, claves, restricciones únicas, índices, reglas `on_delete`).
   - **d)** Diseño del mecanismo de aislamiento multitenant (ver sección 5).
   - **e)** Diseño de la configuración con `.env` y del pipeline de CI.
   - **f)** Contenido previsto de los documentos (`arquitectura.md`, `modelo_fisico.md`, `DoR_DoD.md`).
   - **g)** Plan de trabajo ordenado por pasos, mapeado a las tareas S0-01 … S0-11.
   - **h)** Librerías a instalar, con justificación.
   - **i)** Plan de pruebas.
   - **j)** Supuestos, dudas y decisiones que necesitan mi confirmación (incluye las "observaciones sobre el diagrama" de la sección 4).
   - **k)** Los comandos exactos que **yo** debo ejecutar antes de que empieces (ver sección 3), **sin incluir creación de usuarios de PostgreSQL**, ya que uso `postgres`.
4. **DETENTE** y termina con: *"Esperando tu aprobación para comenzar."*

> **Condición para pasar a la Fase 2:** que yo escriba explícitamente **"APROBADO"** (o "puedes comenzar"). Si pido cambios, ajusta la propuesta y vuelve a presentarla. Sigues sin ejecutar nada hasta recibir la aprobación.

### FASE 2 – EJECUCIÓN

- Implementa **exactamente lo aprobado**, en el orden del plan.
- Si surge algo no contemplado (cambio de diseño, librería extra, conflicto), **detente y pregúntame** antes de improvisar.
- Haz cambios pequeños y verificables; ejecuta pruebas a medida que avanzas.
- No implementes nada fuera del alcance del Sprint 0 (sección 6).

### FASE 3 – INFORME FINAL

Al terminar, genera `docs/INFORME_SPRINT0.md` **y** muestra un resumen en el chat con:

1. **Resumen ejecutivo.**
2. **Estado por tarea** (S0-01, S0-03 … S0-11): ✅ completa / ⚠️ parcial / ❌ pendiente, con una línea de explicación.
3. **Estructura final** de carpetas y apps.
4. **Modelos creados** (tabla por app: modelo, campos clave, relaciones, restricciones).
5. **Migraciones generadas** y confirmación de que se aplican sin errores sobre PostgreSQL.
6. **Mecanismo multitenant** implementado y cómo usarlo en los Sprints siguientes.
7. **Configuración de entorno**: variables definidas en `.env` y su propósito.
8. **CI**: qué hace el pipeline y su estado.
9. **Datos semilla**: qué se carga y con qué comando.
10. **Pruebas**: qué se probó, cuántas pruebas hay y el resultado.
11. **Decisiones técnicas** y su justificación.
12. **Cómo ejecutar el proyecto** (instalación, migraciones, semilla, servidor, pruebas).
13. **Problemas encontrados, deuda técnica y recomendaciones** para el Sprint 1.

---

## 3. PRERREQUISITOS QUE HACE EL USUARIO (NO TÚ)

El usuario se encarga de lo siguiente. **Tú no lo haces**, pero en la propuesta (punto k) debes darme los comandos exactos:

- Instalar PostgreSQL localmente.
- **Tener una base de datos vacía creada** (ya la tengo creada). En local uso el **usuario `postgres`** (superusuario por defecto), por lo que **no hace falta crear usuarios ni dar permisos**: no me propongas comandos para eso. **No crees tablas a mano:** las tablas las crea Django con `migrate`.
- Crear el archivo `backend/.env` a partir de `.env.example` con sus valores reales.
- Crear el repositorio remoto, las ramas GitFlow y el tablero Scrum (tarea S0-02, que **no** es tuya).

Orden esperado: 1) PostgreSQL con BD vacía (usuario `postgres`) → 2) `.env` creado → 3) tú ejecutas `makemigrations`/`migrate` y las tablas aparecen.

---

## 4. CONTEXTO TÉCNICO

### Stack
- Python 3.11+ · Django 5.2 LTS · Django REST Framework
- JWT: `djangorestframework-simplejwt`
- BD: **PostgreSQL**
- Variables de entorno: `python-decouple`
- Documentación de API: `drf-spectacular`
- CORS: `django-cors-headers`
- Pruebas: `pytest` + `pytest-django`

### Estructura actual (ya creada)
```
clinicas-saas/
├── .gitignore
├── README.md
├── docs/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/                 # proyecto Django (startproject ya ejecutado)
│   ├── apps/
│   │   ├── core/
│   │   ├── clinicas/
│   │   ├── seguridad/
│   │   ├── personal/
│   │   ├── pacientes/
│   │   ├── atencion/
│   │   └── ambulancias/
│   └── tests/
└── frontend/
```
Las apps están **vacías** (solo `__init__.py`). Puedes proponer ajustes a esta organización si lo justificas.

### Asignación sugerida de modelos a apps (confírmala o ajústala en tu propuesta)

| App | Modelos |
|---|---|
| `core` | Modelo base abstracto con `clinica`, manager y middleware multitenant, utilidades, comando de semilla |
| `clinicas` | Clinica, PlanSuscripcion, Suscripcion |
| `seguridad` | Usuario (custom user), Roles, UsuarioRol |
| `personal` | Personal, Especialidad, Medico, HorarioAtencion |
| `pacientes` | Paciente, HistoriaClinica, Enfermedad, Alergia |
| `atencion` | Cita, Consulta, Receta, MedicamentoRecetado |
| `ambulancias` | Ambulancia, Equipamiento, Traslado, LicenciaConducir |

### Modelo de datos (según el diagrama de clases)

> Los nombres vienen del diagrama. Usa convenciones de Django (`snake_case` en campos, `PascalCase` en modelos) y propón los tipos de dato.

**Núcleo SaaS**
- **Clinica**: nombre, direccion, telefono, email, nit (único), estado.
- **Plan_Suscripcion**: nombre, precio, max_usuarios, descripcion.
- **Suscripcion**: fecha_inicio, fecha_fin, estado. Clinica 1 → 0..* Suscripcion; Plan 1 → 0..* Suscripcion.

**Seguridad**
- **Usuario**: username, password (hash de Django), email, fecha_creacion, estado. Clinica 1 → 0..* Usuario. El administrador del sistema no tiene clínica. Vínculo opcional con Personal (1 a 0..1) y con Paciente (0..1 ↔ 1, «corresponde a»).
- **Roles**: nombre, descripcion. Clinica «define» 0..* Roles.
- **Usuario_Rol**: fecha_asignacion. Relaciona Usuario ↔ Roles; sin asignaciones duplicadas.

**Personal y médicos**
- **Personal**: ci, nombre, apellido, telefono, cargo, fecha_ingreso, estado. Clinica «emplea» 0..* Personal.
- **Especialidad**: nombre, descripcion.
- **Medico**: numero_colegiatura (único), estado. Personal 1 → 0..1 Medico («ejerce»). Medico → 1 Especialidad («tiene»).
- **Horario_Atencion**: dia_semana, hora_inicio, hora_fin. Medico 1 → 1..* Horario.

**Pacientes**
- **Paciente**: ci, nombre, apellido, sexo, fecha_nacimiento, telefono, email, estado. Clinica «tiene» 0..* Paciente. CI único **por clínica**.
- **Historia_Clinica**: fecha_apertura, grupo_sanguineo, observaciones_generales, estado, fecha_ultima_actualizacion. Paciente 1 ↔ 1 Historia.
- **Enfermedad**: tipo, severidad, fecha_deteccion. Historia 1 → 0..* Enfermedad («registra»).
- **Alergia**: nombre, tipo, severidad, descripcion. Historia 1 → 0..* Alergia («registra»).

**Atención médica**
- **Cita**: fecha, hora, estado, motivo. Clinica «agenda» 0..*; Medico «atiende» 0..*; Paciente «solicita» 0..*.
- **Consulta**: fecha, motivo, observacion, diagnostico. Medico «realiza» 0..*; Paciente «tiene» 0..*; Cita «origina» 0..1 Consulta.
- **Receta**: fecha, indicaciones. Consulta «genera» 0..* Receta.
- **Medicamento_Recetado**: nombre_medicamento, dosis, frecuencia, duracion. Receta 1 → 1..* Medicamento.

**Ambulancias y traslados**
- **Ambulancia**: matricula, tipo, estado, capacidad. Clinica «posee» 0..*.
- **Equipamiento**: nombre, descripcion. Ambulancia «cuenta con» 0..*.
- **Licencia_Conducir**: numero, categoria, fecha_emision, fecha_vencimiento. Personal «posee» 0..1.
- **Traslado**: motivo, fecha_salida, fecha_llegada, tipo_traslado, estado, observacion, lugar_origen, lugar_destino. Ambulancia «realiza» 0..*; Personal «conduce» 0..*; Paciente «es trasladado en» 0..*.

### Observaciones sobre el diagrama (confírmalas conmigo en la propuesta)
1. `Mas_Usuarios` en Plan_Suscripcion es un error de escritura; debe ser **`max_usuarios`**.
2. `Password` debe guardarse **siempre hasheado** (sistema de hashing de Django), nunca en texto plano.
3. `Enfermedad` tiene `tipo` pero no `nombre`: propón si `tipo` guarda el nombre o si se agrega un campo `nombre`.
4. Decide y justifica si `Especialidad` es **global** o **por clínica** (las historias del Sprint 1 indican que cada clínica administra las suyas).
5. El vínculo **Usuario ↔ Personal** no aparece en el diagrama, pero se necesita (historia S1-10). Propón cómo modelarlo.
6. Decide si las entidades hijas (Historia, Enfermedad, Alergia, Receta, Equipamiento, etc.) llevan `clinica` directa o la heredan de su padre; justifica el criterio en términos de seguridad del aislamiento y simplicidad.
7. Propón reglas `on_delete` razonables (por ejemplo `PROTECT` en datos clínicos).

---

## 5. ALCANCE DEL SPRINT 0

### S0-01 · Arquitectura y estrategia multitenant
Documento `docs/arquitectura.md` (1–2 páginas) con: stack, arquitectura en capas (frontend → API REST → servicios → modelos → BD), estrategia multitenant (**BD y esquema compartidos, columna `clinica_id` en cada tabla y middleware de aislamiento**), justificación frente a "una BD por clínica" y un diagrama de bloques (Mermaid dentro del `.md`).

### S0-03 · Entornos y CI básico
- **Todas las variables de entorno, claves y secretos deben estar EXCLUSIVAMENTE en un archivo `.env`.** Nada de claves, contraseñas, hosts o credenciales escritas en el código ni en `settings.py`.
  - `settings.py` lee todo con `python-decouple`.
  - `SECRET_KEY` y credenciales de BD **sin valor por defecto en el código** (si faltan, la aplicación debe fallar con un mensaje claro).
  - `.env` en `.gitignore`. `.env.example` completo y documentado, **sin valores reales**.
  - Incluye en el `.env` las variables necesarias: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, credenciales de PostgreSQL, `CORS_ALLOWED_ORIGINS`, duración de tokens JWT y los datos del administrador del sistema inicial para la semilla (ver S0-11).
- Configuración por entorno (desarrollo y pruebas).
- Pipeline `.github/workflows/ci.yml`: en cada push y pull request, instalar dependencias, levantar un servicio PostgreSQL, aplicar migraciones y ejecutar `pytest`. Los valores de entorno del CI se inyectan desde el propio workflow (valores de prueba, nunca secretos reales).

### S0-04 · Modelo físico de BD
Documento `docs/modelo_fisico.md` con, por tabla: tipos de dato, PK, FK con su regla de borrado, restricciones únicas, índices (al menos en `clinica_id` y campos de búsqueda frecuente como CI y fecha de cita) y un diagrama ER (Mermaid).

### S0-05, S0-06, S0-07 · Modelos y migraciones
- Implementa los modelos de **las 22 entidades** de la sección 4 y genera sus migraciones.
- **Importante:** define `AUTH_USER_MODEL` (modelo `Usuario` personalizado) **antes de la primera migración**; después no se puede cambiar sin rehacer la BD.
- Registra los modelos en el admin de Django (útil para verificar).
- Las migraciones deben aplicarse sin errores sobre PostgreSQL.
- Incluye en los modelos las restricciones de integridad posibles a nivel BD (únicos, `CheckConstraint`, por ejemplo `hora_inicio < hora_fin`, `fecha_fin >= fecha_inicio`).
- **No implementes lógica de negocio, serializers ni endpoints** (eso es del Sprint 1 en adelante).

### S0-08 · Aislamiento multitenant por `clinica_id`
Implementa la base técnica en `apps/core`:
- Un **modelo base abstracto** con FK a `Clinica` para todas las entidades que pertenecen a una clínica.
- Un **manager/queryset** que filtre automáticamente por la clínica activa.
- Un **mecanismo que resuelva la clínica del usuario autenticado** y la deje disponible por petición. Ten en cuenta que con JWT la autenticación ocurre dentro de DRF y no en el middleware de Django estándar: **propón cómo resolverlo de forma robusta** (por ejemplo, un middleware que valide el token, o una clase de autenticación/mixin que fije la clínica activa).
- Al crear registros, la clínica se asigna **desde el usuario autenticado**, nunca desde el body de la petición.
- El administrador del sistema (sin clínica) tiene un tratamiento explícito y documentado.
- **Pruebas:** el usuario de la clínica A no puede listar, leer, modificar ni eliminar datos de la clínica B (cubre al menos los modelos con `clinica` directa).

### S0-10 · Definition of Ready y Definition of Done
Documento `docs/DoR_DoD.md` en español, con 6 a 8 puntos cada uno y adaptado al proyecto (por ejemplo, el DoD debe incluir: pruebas pasando, aislamiento multitenant verificado, Pull Request aprobado y fusionado en `develop`, endpoint documentado en Swagger, migraciones aplicables sin errores, demo aceptada).

### S0-11 · Datos semilla
Comando de gestión (por ejemplo `python manage.py cargar_semilla`) **idempotente** (se puede correr varias veces sin duplicar) que cargue:
- **Planes de suscripción** (por ejemplo Básico, Estándar, Premium, con precio y `max_usuarios`).
- **Roles base:** Administrador de clínica, Recepcionista, Médico, Conductor y Paciente (propón cómo se relacionan con las clínicas, dado que Roles pertenece a una clínica).
- **Especialidades** comunes (Medicina General, Pediatría, Cardiología, Ginecología, Traumatología, etc.).
- El **usuario administrador del sistema inicial**, leyendo su usuario, email y contraseña **desde el `.env`** (nunca escritos en el código).

---

## 6. FUERA DE ALCANCE (NO HACER)

- **S0-02:** repositorio remoto, ramas GitFlow y tablero Scrum (lo hace el usuario).
- **S0-09:** wireframes.
- Cualquier cosa en `frontend/`.
- Serializers, vistas, endpoints y lógica de negocio de las historias del Sprint 1 y 2 (login, CRUDs, validación de suscripción, reglas de citas, etc.).
- Docker, despliegue a producción.

---

## 7. REQUISITOS DE CALIDAD

- Código limpio, comentarios útiles y mensajes de error en **español**.
- Seguridad: contraseñas hasheadas, ningún secreto en el código ni en el repositorio, hash nunca expuesto.
- Documentos claros, en español y en Markdown, dentro de `docs/`.
- `README.md` actualizado con las instrucciones de instalación y arranque.
- `requirements.txt` con versiones fijadas cuando sea posible.
- Todo lo entregado debe poder reproducirse en una máquina limpia siguiendo el README.

---

## 8. INSTRUCCIÓN INICIAL

Comienza ahora con la **FASE 1**: explora el repositorio en modo solo lectura y entrégame tu **propuesta**. **No ejecutes ni modifiques nada** hasta que yo escriba **"APROBADO"**.
