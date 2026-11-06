# Informe del Sprint 0

**SaaS Multitenant de Clínicas · Backend**

Fecha de cierre: 5 de noviembre de 2026

## 1. Resumen ejecutivo

El Sprint 0 deja preparado el backend para que los Sprints 1 y 2 construyan
funcionalidad sobre una base estable:

- 7 apps Django organizadas por dominio (`core`, `clinicas`, `seguridad`,
  `personal`, `pacientes`, `atencion`, `ambulancias`).
- 22 modelos concretos implementados, registrados en el admin y con migraciones
  generadas.
- Aislamiento multitenant por `clinica_id` con `TenantManager` que falla cerrado,
  contexto por petición (`ContextVar`), middleware para sesiones y autenticación JWT
  para DRF.
- Comando de semilla idempotente (`cargar_semilla`) para planes, roles,
  especialidades y administrador del sistema.
- Documentación de arquitectura, modelo físico y DoR/DoD.
- 53 pruebas automatizadas, todas en verde sobre PostgreSQL.
- Pipeline de CI con PostgreSQL 17 listo para ejecutarse en GitHub Actions.

**Estado de cierre:** completo. `backend/.env` fue creado con la base `clinicas_db`,
las migraciones se aplicaron sobre PostgreSQL y la suite completa se ejecutó contra
ese motor con resultado satisfactorio.

## 2. Estado por tarea

| Tarea | Estado | Detalle |
|---|---|---|
| S0-01 · Arquitectura y estrategia multitenant | ✅ Completa | `docs/arquitectura.md` con stack, capas, estrategia, justificación y diagramas Mermaid. |
| S0-02 · Repositorio, ramas y Scrum | ➖ Fuera de alcance | Lo realiza el usuario. |
| S0-03 · Entornos y CI básico | ✅ Completa | `.env.example`, `python-decouple`, secretos sin defaults, `settings_test.py` y `.github/workflows/ci.yml`. |
| S0-04 · Modelo físico de BD | ✅ Completa | `docs/modelo_fisico.md` con 22 tablas, tipos, PK, FK, restricciones, índices y ER. |
| S0-05 · Modelos del núcleo y seguridad | ✅ Completa | `Clinica`, `PlanSuscripcion`, `Suscripcion`, `Usuario`, `Rol`, `UsuarioRol`. |
| S0-06 · Modelos de personal y pacientes | ✅ Completa | `Personal`, `Especialidad`, `Medico`, `HorarioAtencion`, `Paciente`, `HistoriaClinica`, `Enfermedad`, `Alergia`. |
| S0-07 · Modelos de atención y ambulancias | ✅ Completa | `Cita`, `Consulta`, `Receta`, `MedicamentoRecetado`, `Ambulancia`, `Equipamiento`, `LicenciaConducir`, `Traslado`. |
| S0-08 · Aislamiento multitenant | ✅ Completa | Managers, contexto, middleware, autenticación JWT, mixins y 13 pruebas de aislamiento. |
| S0-09 · Wireframes | ➖ Fuera de alcance | Corresponde al frente de diseño. |
| S0-10 · DoR y DoD | ✅ Completa | `docs/DoR_DoD.md` con 8 puntos en cada definición. |
| S0-11 · Datos semilla | ✅ Completa | Comando idempotente `cargar_semilla` y 2 pruebas. |

**Verificación sobre PostgreSQL:** ✅ Completa. Base `clinicas_db`, 24 tablas de
aplicación (22 modelos + 2 tablas M2M de permisos), todas las migraciones aplicadas y
53 pruebas en verde.

## 3. Estructura final

```
clinicas-saas/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   ├── config/
│   │   ├── settings.py
│   │   ├── settings_test.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── core/
│   │   │   ├── tenant.py
│   │   │   ├── managers.py
│   │   │   ├── authentication.py
│   │   │   ├── middleware.py
│   │   │   ├── mixins.py
│   │   │   ├── permissions.py
│   │   │   ├── exceptions.py
│   │   │   ├── admin.py
│   │   │   └── management/commands/cargar_semilla.py
│   │   ├── clinicas/
│   │   ├── seguridad/
│   │   ├── personal/
│   │   ├── pacientes/
│   │   ├── atencion/
│   │   └── ambulancias/
│   └── tests/
│       ├── conftest.py
│       ├── test_modelos.py
│       ├── test_tenant.py
│       ├── test_semilla.py
│       └── test_config.py
├── docs/
│   ├── arquitectura.md
│   ├── modelo_fisico.md
│   ├── DoR_DoD.md
│   └── INFORME_SPRINT0.md
├── frontend/          # sin cambios
├── .gitignore
└── README.md
```

## 4. Modelos creados

### `clinicas`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Clinica` | nombre, direccion, telefono, email, nit, estado | — | `nit` único |
| `PlanSuscripcion` | nombre, precio, max_usuarios, descripcion, activo | — | `nombre` único; precio ≥ 0; max_usuarios > 0 |
| `Suscripcion` | fecha_inicio, fecha_fin, estado | Clinica, Plan | fechas válidas; una suscripción ACTIVA por clínica |

### `seguridad`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Usuario` | username, email, password, fecha_creacion, estado, is_staff | Clinica (nullable), permisos Django | username/email únicos; clínica o superusuario |
| `Rol` | nombre, descripcion, estado | Clinica | único por clínica |
| `UsuarioRol` | fecha_asignacion | Usuario, Rol | único usuario-rol; misma clínica (validación) |

### `personal`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Personal` | ci, nombre, apellido, telefono, cargo, fecha_ingreso, estado | Clinica, Usuario (opcional) | CI única por clínica |
| `Especialidad` | nombre, descripcion, estado | Clinica | única por clínica |
| `Medico` | numero_colegiatura, estado | Clinica, Personal, Especialidad | colegiatura única |
| `HorarioAtencion` | dia_semana, hora_inicio, hora_fin | Medico | hora_inicio < hora_fin; horario exacto único |

### `pacientes`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Paciente` | ci, nombre, apellido, sexo, fecha_nacimiento, telefono, email, estado | Clinica, Usuario (opcional) | CI única por clínica; nacimiento no futuro |
| `HistoriaClinica` | fecha_apertura, grupo_sanguineo, observaciones, estado, actualización | Paciente | una historia por paciente |
| `Enfermedad` | nombre, tipo, severidad, fecha_deteccion | Historia | — |
| `Alergia` | nombre, tipo, severidad, descripcion | Historia | única por historia |

### `atencion`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Cita` | fecha, hora, estado, motivo | Clinica, Medico, Paciente | sin duplicados activos por médico ni por paciente |
| `Consulta` | fecha, motivo, observacion, diagnostico | Clinica, Cita (opcional), Medico, Paciente | coherencia de clínica/médico/paciente con la cita |
| `Receta` | fecha, indicaciones | Consulta | — |
| `MedicamentoRecetado` | nombre_medicamento, dosis, frecuencia, duracion | Receta | — |

### `ambulancias`

| Modelo | Campos clave | Relaciones | Restricciones |
|---|---|---|---|
| `Ambulancia` | matricula, tipo, estado, capacidad | Clinica | matrícula única; capacidad > 0 |
| `Equipamiento` | nombre, descripcion | Ambulancia | único por ambulancia |
| `LicenciaConducir` | numero, categoria, fecha_emision, fecha_vencimiento | Personal | número único; vencimiento > emisión |
| `Traslado` | motivo, fechas, tipo, estado, observacion, origen, destino | Clinica, Ambulancia, Personal, Paciente | llegada ≥ salida |

## 5. Migraciones generadas

Se generaron 10 archivos de migración:

| App | Migraciones |
|---|---|
| `clinicas` | `0001_initial` |
| `seguridad` | `0001_initial` |
| `personal` | `0001_initial`, `0002_initial` |
| `pacientes` | `0001_initial`, `0002_initial` |
| `atencion` | `0001_initial`, `0002_initial` |
| `ambulancias` | `0001_initial`, `0002_initial` |

Las migraciones `0002` existen por las dependencias circulares entre apps (por ejemplo,
`Medico` referencia `Personal` y `Usuario`; `Traslado` referencia varias apps).

Verificaciones realizadas:

- `python manage.py check` → sin errores.
- `python manage.py makemigrations --check --dry-run` → `No changes detected`.
- `python manage.py migrate` sobre SQLite temporal → todas las migraciones aplicadas.
- `python manage.py migrate` sobre PostgreSQL (`clinicas_db`) → todas las migraciones
  aplicadas sin errores.
- `python manage.py showmigrations --plan` → todas las migraciones marcadas con `[X]`.
- Introspección de PostgreSQL → 24 tablas de aplicación: 22 modelos más las tablas
  M2M `seguridad_usuario_groups` y `seguridad_usuario_user_permissions`.

## 6. Mecanismo multitenant

### Uso en los Sprints 1 y 2

```python
from apps.pacientes.models import Paciente

# Lectura: el manager filtra por la clínica activa.
pacientes = Paciente.objects.all()

# Escritura: la clínica se toma del contexto (usuario autenticado).
paciente = Paciente.objects.create(
    ci="123456",
    nombre="Ana",
    apellido="Pérez",
    sexo="F",
    fecha_nacimiento="1990-01-01",
    telefono="70000000",
)
```

- `objects`: filtro automático por clínica. Sin contexto lanza
  `TenantNoConfigurado` (falla cerrado).
- `all_objects`: sin filtro. Solo para autenticación, admin de plataforma, comandos
  de gestión y pruebas explícitas.
- `tenant_context(clinica)` / `tenant_context(bypass=True)`: fija el contexto en
  servicios, comandos y pruebas.
- `TenantMiddleware`: fija la clínica para sesiones y admin de Django.
- `TenantJWTAuthentication`: fija la clínica para peticiones DRF con JWT, leyendo el
  usuario desde la base de datos.
- `TenantViewSetMixin`: base para viewsets; asigna `clinica=request.user.clinica` en
  creación y nunca acepta la clínica desde el body.
- `TieneClinica` y `EsAdminSistema`: permisos base reutilizables.

### Rutas de aislamiento

| Entidad | Ruta |
|---|---|
| Raíces (`Paciente`, `Personal`, `Cita`, etc.) | `clinica` |
| `HistoriaClinica` | `paciente__clinica` |
| `Enfermedad`, `Alergia` | `historia__paciente__clinica` |
| `HorarioAtencion` | `medico__clinica` |
| `UsuarioRol` | `usuario__clinica` |
| `Receta` | `consulta__clinica` |
| `MedicamentoRecetado` | `receta__consulta__clinica` |
| `Equipamiento` | `ambulancia__clinica` |
| `LicenciaConducir` | `personal__clinica` |

## 7. Configuración de entorno

Variables definidas en `backend/.env.example`:

| Variable | Propósito |
|---|---|
| `SECRET_KEY` | Firma criptográfica de Django. Obligatoria, sin default. |
| `DEBUG` | Modo depuración. Default `False`. |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma. |
| `TIME_ZONE` | Zona horaria, default `America/La_Paz`. |
| `DB_NAME` | Nombre de la base PostgreSQL. Obligatoria. |
| `DB_USER` | Usuario PostgreSQL. Obligatoria. |
| `DB_PASSWORD` | Contraseña PostgreSQL. Obligatoria. |
| `DB_HOST` | Host PostgreSQL. Obligatoria. |
| `DB_PORT` | Puerto PostgreSQL. Obligatoria. |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend. |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Vida del access token. |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Vida del refresh token. |
| `ADMIN_SISTEMA_USERNAME` | Usuario del administrador inicial. |
| `ADMIN_SISTEMA_EMAIL` | Email del administrador inicial. |
| `ADMIN_SISTEMA_PASSWORD` | Contraseña del administrador inicial. |
| `SEED_CREAR_CLINICA_DEMO` | Crear clínica demo si no hay ninguna. |
| `SEED_CLINICA_DEMO_NIT` | NIT de la clínica demo. |
| `SEED_CLINICA_DEMO_NOMBRE` | Nombre de la clínica demo. |

`SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` no tienen
valor por defecto: si faltan, Django falla con un mensaje claro en español.

## 8. CI

`.github/workflows/ci.yml` se ejecuta en cada push y pull request:

1. Levanta PostgreSQL 17 como servicio con health check.
2. Configura Python 3.13 con caché de pip.
3. Instala `requirements.txt` con versiones fijadas.
4. Ejecuta `python manage.py check`.
5. Verifica migraciones pendientes con `makemigrations --check --dry-run`.
6. Aplica migraciones con `migrate --noinput`.
7. Ejecuta `pytest`.

Las credenciales del workflow son valores de prueba, no secretos reales. El pipeline
aún no se ha ejecutado en GitHub porque el repositorio no está inicializado en Git
(tarea S0-02 del usuario).

## 9. Datos semilla

Comando:

```bash
python manage.py cargar_semilla
```

Carga de forma idempotente:

- **3 planes:** Básico (29.00, 5 usuarios), Estándar (59.00, 15 usuarios),
  Premium (99.00, 50 usuarios).
- **5 roles por clínica:** Administrador de clínica, Recepcionista, Médico,
  Conductor, Paciente.
- **8 especialidades por clínica:** Medicina General, Pediatría, Cardiología,
  Ginecología, Traumatología, Dermatología, Neurología, Oftalmología.
- **Administrador del sistema:** usuario, email y contraseña desde `.env`, sin clínica
  y con `is_staff`/`is_superuser` activos.
- **Clínica demo opcional:** si no existe ninguna clínica y
  `SEED_CREAR_CLINICA_DEMO=True`, crea una clínica demo configurable.

El comando usa `all_objects` para roles y especialidades, por lo que funciona sin
contexto tenant. Se ejecutó dos veces seguidas en las pruebas sin duplicar datos.

## 10. Pruebas

| Archivo | Pruebas | Cobertura |
|---|---|---|
| `test_modelos.py` | 21 | Restricciones únicas, checks, hashing, integridad referencial. |
| `test_tenant.py` | 13 | Aislamiento, fail-closed, bypass, asignación automática de clínica, hijos y managers de `Usuario`. |
| `test_semilla.py` | 2 | Idempotencia y comportamiento sin clínica demo. |
| `test_config.py` | 2 | `AUTH_USER_MODEL` y registro de los 22 modelos en admin. |
| `test_auth_sesion.py` | 15 | Regresión post-sprint: `ModelBackend`, login por sesión, `/admin/`, `/api/docs/`, no-fuga de contexto, health y raíz. |
| **Total** | **53** | |

Resultado: **53 passed** sobre PostgreSQL (`clinicas_db`) en 5.05 s.

Casos destacados de aislamiento:

- Un usuario de la clínica A no puede listar, leer, actualizar ni eliminar pacientes
  de la clínica B.
- Los modelos hijos se filtran por la clínica de su padre.
- Intentar crear un registro con una clínica distinta lanza `ClinicaAjena`.
- El login resuelve usuarios globalmente antes de conocer la clínica.
- El administrador del sistema requiere bypass explícito.
- `Usuario.objects` es global; `Usuario.tenant_objects` es el manager filtrado.

## 11. Decisiones técnicas

| Decisión | Justificación |
|---|---|
| BD y esquema compartidos con `clinica_id` | Menor costo operativo y de migraciones; suficiente para el alcance del proyecto. |
| `TenantManager` fail-closed | Evita fugas por olvidar filtrar; el acceso global es explícito con `all_objects`. |
| `contextvars` en lugar de `threading.local` | Compatible con código síncrono y asíncrono. |
| `TenantChildModel` con `tenant_lookup` | Evita duplicar `clinica_id` en hijas y mantiene una única fuente de verdad. |
| JWT resuelve la clínica desde la BD | Evita tokens obsoletos si el usuario cambia de clínica o es desactivado. |
| `AUTH_USER_MODEL = "seguridad.Usuario"` | Necesario antes de la primera migración; permite adaptar el usuario al dominio. |
| Email único global | Se eligió unique para simplificar autenticación y evitar ambigüedad. |
| `Especialidad` y `Rol` por clínica | Cada clínica administra su catálogo, como indican las historias del Sprint 1. |
| `Enfermedad` con `nombre` + `tipo` | El diagrama solo tenía `tipo`; se separó el nombre clínico de la clasificación. |
| `on_delete=PROTECT` en datos clínicos | Evita perder historia clínica por borrados accidentales. |
| `SET_NULL` en vínculos Usuario-Personal/Paciente | El registro clínico sobrevive si se elimina la cuenta de usuario. |
| `CASCADE` en composiciones | Hijos como Alergia, Equipamiento o Medicamento no tienen sentido sin su padre. |
| Semilla con clínica demo opcional | Permite cargar roles/especialidades en una instalación nueva sin imponer datos reales. |

## 12. Cómo ejecutar el proyecto

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # completar valores reales
python manage.py migrate
python manage.py cargar_semilla
python manage.py runserver
```

Pruebas:

```bash
pytest
```

Documentación API:

- Swagger UI: <http://localhost:8000/api/docs/>
- Esquema OpenAPI: <http://localhost:8000/api/schema/>
- Admin: <http://localhost:8000/admin/>

## 13. Problemas encontrados, deuda técnica y recomendaciones

### Problemas encontrados

1. **`backend/.env` ausente al inicio:** bloqueó temporalmente la conexión a
   PostgreSQL. Se resolvió cuando el usuario creó el archivo con la base `clinicas_db`;
   después se aplicaron las migraciones y se ejecutó la suite contra PostgreSQL.
2. **Contraseña de PostgreSQL no disponible al inicio:** `psql -U postgres -h localhost
   -w` fallaba con `fe_sendauth: no password supplied`. No se crearon usuarios ni tablas
   manualmente; el usuario proporcionó las credenciales mediante `.env`.
3. **Migraciones generadas con SQLite temporal:** se usó una configuración externa al
   proyecto para no bloquear el avance mientras faltaba `.env`. Posteriormente se
   aplicaron sin errores sobre PostgreSQL, confirmando que el esquema es portable.
4. **`full_clean()` requiere contexto tenant en modelos tenant:** al validar
   restricciones, Django usa el `_default_manager` del modelo; para modelos con
   `TenantManager` fuera de un contexto lanza `TenantNoConfigurado`. Es coherente
   con el diseño fail-closed, pero los formularios y servicios deben ejecutarse dentro
   del contexto de la petición. `Usuario` es la excepción: su default es global por
   exigencia de la autenticación de Django.

### Deuda técnica

- `Medico.numero_colegiatura` y `Ambulancia.matricula` son únicos globalmente, no por
  clínica. Se mantuvo así porque la colegiatura y la matrícula suelen ser únicas a
  nivel país; revisar si el negocio requiere otra cosa.
- No hay endpoints ni serializers: es intencional, corresponden al Sprint 1.
- El admin de plataforma usa `all_objects`; conviene agregar auditoría de accesos
  globales en una etapa posterior.
- La clínica demo de la semilla es un dato de desarrollo; en producción debe
  configurarse `SEED_CREAR_CLINICA_DEMO=False`.
- **Revisión obligatoria en Sprint 1:** `Personal.usuario` y `Paciente.usuario` deben
  validar que el usuario pertenezca a la misma clínica que el registro. Hoy son FK
  nullable sin esa restricción a nivel de modelo; los formularios y serializers tenant
  deben filtrar con `Usuario.tenant_objects` y rechazar usuarios de otra clínica.

### Recomendaciones para el Sprint 1

1. El entorno PostgreSQL ya está listo con `clinicas_db`, migraciones aplicadas y
   semilla cargada; iniciar el Sprint 1 directamente sobre esta base.
2. Implementar los viewsets heredando de `TenantViewSetMixin` y cubrir cada uno con
   pruebas de aislamiento entre dos clínicas.
3. Definir la matriz de permisos por rol y conectarla a `TieneClinica`.
4. Validar la suscripción activa de la clínica en un permission o servicio transversal.
5. Documentar cada endpoint en Swagger y verificar el esquema en CI.
6. Ejecutar el workflow de CI en el repositorio remoto una vez creado (S0-02).
7. Revisar `Personal.usuario` y `Paciente.usuario` para exigir que el usuario pertenezca
   a la misma clínica del registro.

## 14. Corrección post-sprint

### Síntoma

Al abrir `/admin/`, `/api/docs/` o `/`, el backend devolvía HTTP 500 con
`TenantNoConfigurado`. El traceback pasaba por:

```text
django/contrib/auth/backends.py  get_user -> UserModel._default_manager.get(pk=...)
apps/seguridad/models.py         UsuarioManager.get_queryset -> get_clinica_actual()
apps/core/middleware.py          TenantMiddleware -> request.user.is_authenticated
```

### Causa raíz

`Usuario.objects` era el `_default_manager` y filtraba por clínica. Django lo usa en
`ModelBackend.authenticate()` (`get_by_natural_key`) y en `ModelBackend.get_user()`
(`get(pk=...)`) **antes** de que exista contexto de clínica. El flujo era circular:
para cargar al usuario desde la sesión hacía falta contexto, y el contexto solo se
fijaba después de cargar al usuario.

### Corrección aplicada

| Elemento | Antes | Después |
|---|---|---|
| `Usuario.objects` | Filtraba por clínica | Global; es el `_default_manager` |
| `Usuario.tenant_objects` | No existía | Manager explícito, fail-closed, `use_in_migrations=False` |
| `Usuario.all_objects` | `UserManager()` global | Sin cambios |
| `UsuarioManager.get_by_natural_key` | Delegaba en `all_objects` | Eliminado; el default ya es global |
| `AUTHENTICATION_BACKENDS` | Implícito | Explícito: `ModelBackend` |
| `TenantMiddleware` | Limpiaba antes y después | `contexto_limpio()` con tokens de `ContextVar` y `try/finally` |
| Rutas | Solo `/admin/`, `/api/schema/`, `/api/docs/` | Se agregan `/api/health/` y `/` → `/api/docs/` |

`TenantMiddleware` sigue fijando la clínica del usuario autenticado y activa el bypass
explícito cuando el usuario es superusuario sin clínica. No se generó ninguna migración:
el esquema no cambia, solo el comportamiento en Python.

### Pruebas de regresión añadidas

`tests/test_auth_sesion.py` (15 pruebas) cubre:

- `ModelBackend.authenticate()` y `get_user()` sin contexto para el admin del sistema
  y para un usuario con clínica.
- `Usuario._default_manager is Usuario.objects`.
- `GET /admin/` sin sesión → 302 al login (nunca 500).
- Login por formulario del admin del sistema y de un usuario con clínica, seguido de
  `GET /admin/` y `GET /api/docs/` con la cookie ya establecida.
- `force_login`, `client.login()` y `logout()` para ambos tipos de usuario.
- `Usuario.objects` global frente a `Usuario.tenant_objects` filtrado y fail-closed.
- No-fuga de contexto: una petición con usuario de la clínica A seguida de una petición
  anónima en el mismo hilo; la segunda no hereda clínica ni bypass.
- Restauración del contexto incluso si la vista lanza una excepción.
- `/api/health/` sin sesión y `/` redirigiendo a `/api/docs/`.

También se actualizó `tests/test_tenant.py` para distinguir `objects` (global) de
`tenant_objects` (tenant) y `tests/conftest.py` para crear usuarios con el manager por
defecto, cubriendo el camino real de autenticación.

### Por qué la suite original de 37 pruebas no lo detectó

- Las pruebas de modelos usaban el ORM directamente, sin `Client` ni middleware.
- Las pruebas tenant ejecutaban `Usuario.objects` **dentro** de `tenant_context`; una
  de ellas incluso afirmaba el comportamiento defectuoso (que filtrara).
- `conftest.py` creaba los usuarios con `Usuario.all_objects`, saltándose el manager
  por defecto.
- No había ninguna petición HTTP autenticada, ni `force_login`, ni `login()`, ni
  `GET /admin/` o `/api/docs/`.
- El fallo aparecía en la **segunda** petición, cuando `AuthenticationMiddleware` carga
  el usuario desde la sesión; ninguna prueba hacía esa segunda petición.

### Verificación final

```text
python manage.py check                        -> System check identified no issues
python manage.py makemigrations --check       -> No changes detected
pytest (config.settings_test, PostgreSQL)     -> 53 passed in 5.05s
```
