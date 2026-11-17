# Informe del Sprint 1

**SaaS Multitenant de Clínicas · Backend**

Fecha de cierre: 6 de noviembre de 2026

## 1. Resumen ejecutivo

El Sprint 1 incorpora la capa de negocio sobre la base multitenant del Sprint 0:

- Autenticación JWT con login, refresh rotativo, logout con blacklist, perfil,
  cambio de contraseña y validación del estado de la clínica en cada petición.
- Gestión de clínicas con provisión atómica de roles base, especialidades base y
  primer administrador.
- Planes, suscripciones, renovación, cambio de plan y cancelación.
- Usuarios, roles, asignaciones usuario-rol, personal, especialidades, médicos y
  horarios.
- Aislamiento por clínica en todas las consultas y escrituras.
- Modo restringido para Administradores de clínica sin suscripción vigente.
- Validación de `max_usuarios` con control de concurrencia.
- Documentación OpenAPI/Swagger con botón **Authorize** (Bearer JWT) y catálogo de
  códigos de error de negocio.

**Estado de cierre:** completo. La suite pasa de **53** a **135 pruebas**, todas en
verde sobre PostgreSQL (`clinicas_db`, `config.settings_test`). `makemigrations
--check --dry-run` responde `No changes detected` después de aplicar las migraciones
de `rest_framework_simplejwt.token_blacklist`.

## 2. Decisiones aplicadas

| Decisión | Implementación |
|---|---|
| D1 · Modo restringido server-side | `TieneSuscripcionVigente` bloquea la lectura de clínicas, usuarios, roles, usuario-roles, personal, especialidades, médicos y horarios con `403 suscripcion_vencida`. El perfil, los planes y las suscripciones siguen accesibles. |
| D2 · Registro atómico de clínica | `registrar_clinica` crea clínica, roles, especialidades y primer admin en una transacción. El admin es `is_staff=False`, sin password expuesta. |
| D3 · Datos base compartidos | `apps/core/seed_data.py` es la fuente única para semilla y provisión de clínicas. |
| D4 · Roles base protegidos | No se renombran, desactivan ni eliminan; solo se edita la descripción. Se protege el último administrador activo. |
| D5 · Vigencia al vuelo | `suscripcion_vigente` evalúa `ACTIVA` y fechas inclusivas; `marcar_vencidas` actualiza oportunistamente. |
| D6 · Límite de usuarios | `max_usuarios` cuenta usuarios activos. Creación y reactivación usan `select_for_update` sobre la clínica. |
| D7 · Relaciones tenant | `TenantRelatedField` resuelve el queryset por petición y falla cerrado. |
| D8 · Logout seguro | Blacklist de SimpleJWT y rotación de refresh. |
| D9 · API versionada | Rutas `/api/v1/`, paginación 20/100, búsqueda y ordenamiento DRF, sin `django-filter`. |

### Ajustes obligatorios aprobados

1. **Modo restringido en servidor:** permiso `TieneSuscripcionVigente` en todos los
   endpoints de negocio; no depende solo del claim del token.
2. **Bootstrap de S1-01:** el primer administrador no valida `max_usuarios` ni
   suscripción. La creación normal sin suscripción responde
   `403 suscripcion_vencida`.
3. **Concurrencia real:** prueba con `@pytest.mark.django_db(transaction=True)`;
   exactamente un `201` y un `409 limite_usuarios`.
4. **Swagger Bearer:** `TenantJWTAuthenticationScheme` registra el esquema Bearer y
   habilita el botón **Authorize** en `/api/docs/`.
5. **Médico sin vínculo:** `/medicos/` y `/horarios/` devuelven `200` con lista
   vacía, nunca `500`.
6. **Cambio de contraseña:** `POST /api/v1/auth/cambiar-password/` exige la
   contraseña actual, aplica los validadores de Django, solo afecta al usuario
   autenticado y tiene pruebas de éxito y error.
7. **Códigos documentados:** catálogo completo en Swagger y en este informe.

## 3. Endpoints entregados

Base: `/api/v1/`.

| Método | Ruta | Permiso |
|---|---|---|
| POST | `/auth/login/` | Público (throttle 5/min). |
| POST | `/auth/refresh/` | Público. |
| POST | `/auth/logout/` | Autenticado. |
| GET | `/auth/me/` | Autenticado. |
| POST | `/auth/cambiar-password/` | Autenticado. |
| GET/POST | `/clinicas/` | Listado: admin sistema o de clínica. Creación: admin sistema. |
| GET/PUT/PATCH/DELETE | `/clinicas/{id}/` | Admin sistema (lectura también admin de clínica). |
| GET | `/planes/` | Admin sistema o de clínica (también en modo restringido). |
| POST/PUT/PATCH/DELETE | `/planes/` | Admin sistema. |
| GET/POST | `/suscripciones/` | Admin sistema (lectura) / admin de clínica. |
| GET | `/suscripciones/{id}/` | Admin sistema o de clínica. |
| POST | `/suscripciones/{id}/renovar/` | Admin de clínica. |
| POST | `/suscripciones/{id}/cambiar-plan/` | Admin de clínica. |
| POST | `/suscripciones/{id}/cancelar/` | Admin de clínica. |
| CRUD | `/usuarios/` | Admin de clínica con suscripción. |
| CRUD | `/roles/` | Admin de clínica con suscripción. |
| GET/POST/DELETE | `/usuario-roles/` | Admin de clínica con suscripción. |
| CRUD | `/personal/` | Admin de clínica con suscripción. |
| POST | `/personal/{id}/vincular-usuario/` | Admin de clínica. |
| GET | `/especialidades/` | Admin de clínica o médico con suscripción. |
| POST/PUT/PATCH/DELETE | `/especialidades/` | Admin de clínica con suscripción. |
| GET | `/medicos/` | Admin de clínica o médico (el médico solo ve su registro). |
| POST/PUT/PATCH/DELETE | `/medicos/` | Admin de clínica con suscripción. |
| GET | `/horarios/` | Admin de clínica o médico (el médico solo ve los suyos). |
| POST/PUT/PATCH/DELETE | `/horarios/` | Admin de clínica o médico (el médico solo sobre los suyos). |

## 4. Códigos de error de negocio

Formato uniforme:

```json
{
  "codigo": "limite_usuarios",
  "mensaje": "La clínica alcanzó el máximo de usuarios de su plan.",
  "detalles": {"usuarios_activos": 5, "max_usuarios": 5}
}
```

| Código | HTTP | Significado |
|---|---|---|
| `credenciales_invalidas` | 401 | Usuario o contraseña incorrectos. |
| `no_autenticado` | 401 | Token ausente, inválido o usuario inactivo. |
| `permiso_denegado` | 403 | El rol no permite la operación. |
| `suscripcion_vencida` | 403 | La clínica no tiene suscripción vigente. |
| `clinica_inactiva` | 403 | Clínica desactivada (login, token ya emitido o refresh). |
| `sin_clinica` | 403 | Usuario no superusuario sin clínica. |
| `medico_no_vinculado` | 403 | Médico sin Personal/Médico vinculado. |
| `datos_invalidos` | 400 | Error de validación de campos. |
| `password_invalida` | 400 | La contraseña no cumple los validadores de Django. |
| `password_actual_invalida` | 400 | La contraseña actual no coincide. |
| `password_repetida` | 400 | La nueva contraseña es igual a la actual. |
| `refresh_invalido` | 401 | Refresh token inválido, expirado o en blacklist. |
| `nit_duplicado` | 409 | Ya existe una clínica con ese NIT. |
| `usuario_duplicado` | 409 | Username no disponible. |
| `email_duplicado` | 409 | Email no disponible. |
| `clinica_duplicada` | 409 | Conflicto de unicidad al provisionar la clínica. |
| `limite_usuarios` | 409 | Se alcanzó `max_usuarios` del plan. |
| `plan_inactivo` | 409 | El plan seleccionado no está activo. |
| `suscripcion_activa` | 409 | La clínica ya tiene una suscripción activa. |
| `suscripcion_no_vigente` | 409 | No se puede renovar una suscripción no vigente. |
| `suscripcion_no_activa` | 409 | No se puede cancelar una suscripción no activa. |
| `fechas_invalidas` | 400 | Fecha de fin anterior a la de inicio. |
| `fecha_fin_invalida` | 400 | La nueva fecha de fin no extiende la actual. |
| `ultimo_administrador` | 409 | Se intenta dejar la clínica sin admin activo. |
| `rol_base_protegido` | 409 | Intento de renombrar, desactivar o borrar un rol base. |
| `rol_duplicado` | 409 | Ya existe un rol con ese nombre. |
| `rol_con_asignaciones` | 409 | El rol tiene asignaciones. |
| `rol_ya_asignado` | 409 | El usuario ya tiene ese rol. |
| `rol_ajeno` | 409 | El rol pertenece a otra clínica. |
| `rol_inactivo` | 409 | El rol está inactivo. |
| `ci_duplicada` | 409 | CI duplicada en la clínica. |
| `personal_ya_es_medico` | 409 | El personal ya tiene médico asociado. |
| `colegiatura_duplicada` | 409 | Número de colegiatura ya registrado. |
| `especialidad_duplicada` | 409 | Especialidad duplicada en la clínica. |
| `especialidad_en_uso` | 409 | La especialidad tiene médicos asociados. |
| `horario_solapado` | 409 | El horario se solapa con otro del médico. |
| `horario_invalido` | 400 | Hora de inicio mayor o igual a la de fin. |
| `medico_requerido` | 400 | Falta el médico al crear un horario como admin. |
| `personal_con_medico` | 409 | No se puede borrar personal con médico. |
| `usuario_ya_vinculado` | 409 | El usuario ya está vinculado a otro personal. |
| `no_encontrado` | 404 | El recurso no existe o es de otra clínica. |
| `demasiados_intentos` | 429 | Throttling del login. |

## 5. Pruebas

### Totales

- Suite completa: **135 passed**.
- Nuevas pruebas del Sprint 1: **82**.
- Suite previa del Sprint 0: **53**, sin regresiones.

### Cobertura por módulo

| Archivo | Pruebas | Contenido |
|---|---|---|
| `tests/api/test_auth_api.py` | 20 | Login, modo restringido, refresh, logout, perfil, cambio de password, no fuga JWT y bloqueo por clínica inactiva. |
| `tests/api/test_clinicas_api.py` | 16 | Registro atómico, bootstrap, duplicados, planes, contratación, renovación, cambio de plan y cancelación. |
| `tests/api/test_usuarios_api.py` | 17 | CRUD de usuarios, límites, reactivación, roles base, asignaciones y concurrencia real. |
| `tests/api/test_personal_api.py` | 17 | Personal, especialidades, médicos, horarios, médico sin vínculo y reglas de agenda. |
| `tests/api/test_aislamiento_api.py` | 7 | Matriz de aislamiento por clínica: listado, detalle, PATCH, DELETE y relaciones cruzadas. |
| `tests/api/test_flujo_completo_api.py` | 1 | Flujo E2E: clínica → admin → suscripción → usuario → personal → médico → horario. |
| `tests/api/test_openapi.py` | 4 | Bearer JWT, catálogo de códigos, rutas del Sprint 1 y Swagger UI. |

### Verificaciones clave

- Administrador de clínica sin suscripción:
  - `403 suscripcion_vencida` en clínicas (lectura), usuarios, roles,
    usuario-roles, personal, especialidades, médicos y horarios.
  - `200` en `/auth/me/`, `GET /planes/` y endpoints de suscripción.
- Concurrencia de `max_usuarios`: un `201`, un `409 limite_usuarios`.
- Médico sin Personal/Médico: `/medicos/` y `/horarios/` devuelven `[]`.
- Cambio de contraseña: valida contraseña actual, validadores de Django y solo
  afecta al usuario autenticado.
- Aislamiento: los recursos de otra clínica responden `404 no_encontrado` en
  listado, detalle, PATCH y DELETE; las relaciones cruzadas responden
  `400 datos_invalidos`.
- Clínica desactivada: un token ya emitido responde `403 clinica_inactiva`, el
  refresh se rechaza y al reactivar la clínica el acceso se restablece.
- El administrador del sistema (sin clínica) no se ve afectado por el estado de
  una clínica.
- Contraseñas nunca aparecen en respuestas.

## 6. Configuración relevante

- `SPECTACULAR_SETTINGS` documenta título, descripción, catálogo de errores y
  esquema Bearer mediante `TenantJWTAuthenticationScheme`.
- `SIMPLE_JWT`: rotación de refresh, blacklist tras rotación y access de 60 min.
- `DEFAULT_THROTTLE_RATES["login"]`: configurable con `LOGIN_THROTTLE_RATE`
  (por defecto `5/min`).
- `tenant_objects` en la API y `all_objects` solo en operaciones auditadas.
- `TenantJWTAuthentication` valida usuario activo y clínica activa en cada petición,
  usando `select_related("clinica")` para no agregar consultas.
- `RefreshTokenSerializer` también rechaza una clínica inactiva antes de rotar el
  token.
- `rest_framework_simplejwt.token_blacklist` agregada a `INSTALLED_APPS` y migrada.
- Sin nuevas librerías: solo se habilitó la app de blacklist ya incluida en
  SimpleJWT.

## 7. Verificación ejecutada

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected

python manage.py migrate
token_blacklist.0001 ... token_blacklist.0013 aplicadas

python manage.py makemigrations --check --dry-run
No changes detected

pytest -q
135 passed
```

## 8. Estructura añadida

```text
backend/apps/core/
├── api_exceptions.py      # formato uniforme y excepciones de negocio
├── fields.py              # TenantRelatedField
├── pagination.py          # 20/100
├── permissions.py         # TieneSuscripcionVigente y roles
├── querysets.py           # queryset tenant seguro para OpenAPI
├── schema.py              # Bearer JWT en Swagger
├── seed_data.py           # datos base compartidos
└── throttles.py           # throttle de login

backend/apps/clinicas/
├── serializers.py
├── services.py
├── urls.py
└── views.py

backend/apps/seguridad/
├── serializers.py
├── services.py
├── urls.py
└── views.py

backend/apps/personal/
├── serializers.py
├── services.py
├── urls.py
└── views.py

backend/tests/api/
├── conftest.py
├── helpers.py
├── test_auth_api.py
├── test_clinicas_api.py
├── test_usuarios_api.py
├── test_personal_api.py
├── test_aislamiento_api.py
├── test_flujo_completo_api.py
└── test_openapi.py
```

## 9. Estado por historia de usuario (S1-01 … S1-14)

| ID | Estado | Evidencia / una línea |
|---|---|---|
| S1-01 | ✅ | `POST /clinicas/` registra la clínica y provisiona roles, especialidades y primer admin en una transacción; NIT único y bootstrap sin validar suscripción ni `max_usuarios`. |
| S1-02 | ✅ | CRUD de `/planes/` reservado al administrador del sistema, con `precio >= 0`, `max_usuarios >= 1` y baja lógica (`activo=False`). |
| S1-03 | ✅ | Contratación, renovación, cambio de plan y cancelación; solo una suscripción `ACTIVA` por clínica. |
| S1-04 | ✅ | Vigencia calculada al vuelo y `max_usuarios` con `select_for_update`; prueba de concurrencia con un `201` y un `409`. |
| S1-05 | ✅ | Login, refresh rotativo, logout con blacklist y `/auth/me/`; contraseñas hasheadas y nunca expuestas. |
| S1-06 | ✅ | CRUD de `/usuarios/` acotado al tenant; la clínica sale del request, se protege el último admin y se respeta el cupo. |
| S1-07 | ✅ | CRUD de `/roles/` y `/usuario-roles/`; roles base protegidos y asignaciones duplicadas rechazadas. |
| S1-08 | ✅ | Permisos por rol en todos los viewsets; los endpoints de negocio exigen suscripción vigente en servidor. |
| S1-09 | ✅ | CRUD de `/personal/` con aislamiento por clínica, baja lógica y validación de CI duplicada. |
| S1-10 | ✅ | `POST /personal/{id}/vincular-usuario/` maneja el vínculo 1:1 y rechaza usuarios de otra clínica. |
| S1-11 | ✅ | CRUD de `/especialidades/` por clínica, unicidad por tenant y bloqueo de borrado si está en uso. |
| S1-12 | ✅ | CRUD de `/medicos/` con especialidad, colegiatura única y relación 1:1 con `Personal`. |
| S1-13 | ✅ | `/horarios/` para admin y médico; el médico solo opera los suyos y se valida solapamiento. |
| S1-14 | ✅ | Matriz de aislamiento completa para las 7 entidades (listado, detalle, PATCH/DELETE según los métodos disponibles) y relaciones cruzadas de médico y horario. |

**Lectura:** las 14 historias del Sprint 1 quedan completas.

## 10. Decisiones técnicas

Además de las decisiones D1–D9, se tomaron estas decisiones de implementación:

| Tema | Decisión | Motivo |
|---|---|---|
| Contexto tenant | `ContextVar` + `TenantMiddleware` para sesiones y `TenantJWTAuthentication` para JWT. | Aislamiento por petición, compatible con código síncrono y asíncrono, y limpieza garantizada en `finally`. |
| Managers de `Usuario` | `Usuario.objects` global para Django auth; `Usuario.tenant_objects` para la API; `all_objects` solo en operaciones auditadas. | Evita romper `ModelBackend.authenticate()` y la carga de sesión antes de que exista contexto de clínica. |
| Relaciones tenant | `TenantRelatedField` resuelve el queryset en cada petición y falla cerrado sin contexto. | Impide asociar roles, usuarios, personal, especialidades o médicos de otra clínica. |
| Reglas de negocio | La lógica vive en servicios (`services.py`); los serializers validan forma y tipos. | Los conflictos devuelven `409` con código estable en lugar de un `400` genérico. |
| Validadores únicos | Se desactivan `UniqueValidator`/`UniqueTogetherValidator` cuando el servicio ya devuelve un código de negocio. | Evita que DRF responda antes con `datos_invalidos` y se pierda el código específico. |
| Suscripciones | Vigencia inclusiva (`fecha_inicio <= hoy <= fecha_fin`) y marcado oportunista de vencidas. | No requiere tarea programada para el Sprint 1 y mantiene datos consistentes. |
| JWT | Los claims incluyen `clinica_id` y `roles`, pero la autenticación vuelve a consultar la BD con `select_related("clinica")`. | Un token viejo no conserva privilegios si el usuario o su clínica cambian, sin agregar consultas extra. |
| Clínica activa | `TenantJWTAuthentication` y el refresh rechazan una clínica con `estado=False` mediante `ClinicaInactiva` (`403 clinica_inactiva`). | El bloqueo es inmediato, no espera a que expire el token ni depende del login. |
| Contraseñas | `write_only`, hashing de Django y `is_staff=False` para el admin de clínica. | Nunca se serializa el hash y el admin de clínica no accede al admin de Django. |
| API | `/api/v1/`, paginación 20/100, `SearchFilter` y `OrderingFilter`. | Contrato estable y sin dependencia de `django-filter` en este sprint. |
| OpenAPI | `TenantJWTAuthenticationScheme` + seguridad por operación; el login y el refresh van sin seguridad. | Habilita **Authorize** en Swagger sin declarar seguridad global duplicada. |
| Login | Throttle configurable con `LOGIN_THROTTLE_RATE` (por defecto `5/min`). | Mitiga fuerza bruta sin bloquear el resto de la API. |

## 11. Cómo ejecutar el proyecto

### Requisitos

- Python 3.11 o superior (probado con 3.13).
- PostgreSQL 17 con una base vacía creada (`clinicas_db` en el ejemplo).
- Node.js 20+ solo si se trabaja en `frontend/` (fuera del alcance del Sprint 1).

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Completar SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT,
# ADMIN_SISTEMA_USERNAME, ADMIN_SISTEMA_EMAIL y ADMIN_SISTEMA_PASSWORD.

.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py cargar_semilla
.\venv\Scripts\python.exe manage.py runserver
```

- API: `http://127.0.0.1:8000/api/v1/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/` (botón **Authorize** con el `access`)
- Esquema OpenAPI: `http://127.0.0.1:8000/api/schema/`
- Salud: `http://127.0.0.1:8000/api/health/` (sin autenticación)

### Pruebas

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```

`pytest.ini` usa `config.settings_test`, que hereda la configuración real y aplica un
hasher rápido. Las pruebas requieren PostgreSQL y permisos para crear la base de
pruebas. No usar el `python` global: el proyecto está preparado para el Python del
`venv`.

### Verificaciones de cierre

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py spectacular --validate --file schema.yaml
```

## 12. Problemas encontrados

| Problema | Causa | Solución aplicada |
|---|---|---|
| `TenantNoConfigurado` al cargar la sesión | `ModelBackend` usaba un manager filtrado antes de existir contexto de clínica. | `Usuario.objects` global para auth y `tenant_objects` explícito para la API. |
| Generación de OpenAPI fallaba | Los viewsets consultaban managers tenant sin contexto durante el esquema. | `queryset_tenant()` devuelve vacío en generación de esquema. |
| `TypeError` al combinar permisos | DRF 3.16 compone clases con `|`, no instancias. | Permisos compuestos explícitos: `EsAdminSistemaOAdminClinica` y `EsAdminClinicaOMedico`. |
| Errores 404 con formato distinto | `get_object()` lanza `Http404`, no `NotFound` de DRF. | El manejador normaliza ambos a `no_encontrado`. |
| Conflictos únicos devolvían `400` | `UniqueValidator` y `UniqueTogetherValidator` se ejecutaban antes del servicio. | Se desactivaron en los serializers cuyos servicios ya devuelven `409`. |
| Seguridad duplicada en Swagger | `SECURITY` global más la seguridad por operación generaban entradas repetidas. | Se eliminó el `SECURITY` global y se dejó la declaración por operación. |
| El médico no podía crear su horario | El serializer exigía `medico` aunque el servidor lo resuelve desde el vínculo. | `medico` opcional en el serializer y resolución server-side; `medico_requerido` para admin. |
| Prueba de concurrencia inestable | Conexiones abiertas entre hilos. | `transaction=True`, barrera y `connections.close_all()` en cada hilo. |
| Código de refresh inconsistente | `/auth/refresh/` responde `datos_invalidos` y `/auth/logout/` responde `refresh_invalido`. | Pendiente de unificación (ver deuda técnica). |
| Clínica desactivada con tokens vivos | La validación de `clinica.estado` solo existía en el login. | Se validó en `TenantJWTAuthentication` y en `RefreshTokenSerializer` con `403 clinica_inactiva`. |

## 13. Deuda técnica

| Prioridad | Tema | Riesgo | Propuesta |
|---|---|---|---|
| Media | Revocación de access tokens | El logout solo invalida el refresh; el access sigue válido hasta 60 minutos. | Acortar la vida del access, agregar versión de token o blacklist de access si el requisito lo exige. |
| Media | Código de error de refresh | `/auth/refresh/` devuelve `datos_invalidos`; `/auth/logout/` devuelve `refresh_invalido`. | Unificar contrato en el serializer y documentarlo. |
| Media | Filtros de negocio | Solo hay búsqueda y ordenamiento; no hay filtros por fecha, estado ni relaciones. | Evaluar `django-filter` en Sprint 2 cuando crezcan pacientes y citas. |
| Baja | Baja de clínica | El soft delete no desactiva usuarios ni cancela suscripciones automáticamente. | Definir política de desactivación en cascada y auditoría. |
| Baja | Observabilidad | No hay logs estructurados ni métricas de errores de negocio. | Añadir logging de códigos y correlación por petición. |
| Baja | Contrato OpenAPI | Las descripciones de error son manuales y pueden desactualizarse. | Validar el catálogo de códigos en CI (ya existe una prueba base). |

## 14. Recomendaciones para el Sprint 2

1. **Unificar el contrato de refresh** y revisar la revocación de access tokens
   según el nivel de seguridad requerido.
2. **Mantener la matriz de aislamiento y el flujo E2E** al agregar pacientes y
   citas; así las nuevas entidades nacen con la misma cobertura.
3. **Definir filtros y paginación de las nuevas entidades** (pacientes, citas,
   historias) y evaluar `django-filter` si la complejidad lo justifica.
4. **Mantener la clínica fuera del payload** en todos los recursos nuevos y reutilizar
   `TenantRelatedField` para cualquier relación entre tenants.
5. **Revisar límites del plan** más allá de `max_usuarios` (por ejemplo, pacientes o
   citas) cuando el negocio lo defina.
6. **Añadir auditoría y trazabilidad** de cambios sensibles: desactivación de
   clínicas/usuarios, cambios de plan y accesos a datos clínicos.
7. **Cuidar datos de salud:** minimización, control de acceso por rol y registro de
   accesos desde el diseño de pacientes e historias clínicas.
8. **Optimizar consultas** con `select_related`/`prefetch_related` antes de que crezcan
   los listados; añadir pruebas de número de consultas donde sea crítico.
9. **Fortalecer CI:** ejecutar la suite con PostgreSQL, `check`, `makemigrations
   --check` y `spectacular --validate`; considerar umbral de cobertura.
10. **Mantener el contrato documental:** actualizar el catálogo de errores y Swagger en
    cada historia, con una prueba que verifique los códigos nuevos.

## 15. Commits sugeridos

```text
feat(core): infraestructura de errores, permisos, campos y paginación tenant
feat(seguridad): autenticación JWT, modo restringido, usuarios, roles y cambio de password
feat(clinicas): registro atómico de clínicas, planes y ciclo de suscripciones
feat(personal): personal, especialidades, médicos y horarios con aislamiento
test(api): 82 pruebas de auth, negocio, aislamiento, E2E, concurrencia y OpenAPI
docs(sprint1): informe, arquitectura de API y catálogo de códigos de error
```
