# SaaS Multitenant de Clínicas

Monorepo con `backend/` (Python + Django REST Framework) y `frontend/` (React + Vite).

El Sprint 0 entrega la base del backend: configuración por entorno, 22 modelos con
migraciones, aislamiento multitenant por `clinica_id`, datos semilla, documentación y
pruebas automatizadas.

El Sprint 1 incorpora la API de negocio bajo `/api/v1/`: autenticación JWT, modo
restringido por suscripción, clínicas, planes, suscripciones, usuarios, roles,
personal, especialidades, médicos y horarios. La suite suma **128 pruebas** en verde.

## Requisitos

- Python 3.11 o superior (probado con 3.13).
- PostgreSQL 17 con una base de datos vacía.
- Node.js 20+ (solo para el frontend).

## Backend

### 1. Crear el entorno virtual e instalar dependencias

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia la plantilla y completa los valores reales:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Variables obligatorias (sin valor por defecto en el código):

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Genera una nueva para cada entorno. |
| `DB_NAME` | Nombre de la base de datos PostgreSQL ya creada. |
| `DB_USER` | Usuario de PostgreSQL (en local suele ser `postgres`). |
| `DB_PASSWORD` | Contraseña del usuario de PostgreSQL. |
| `DB_HOST` | Host de PostgreSQL (`localhost` en desarrollo). |
| `DB_PORT` | Puerto de PostgreSQL (`5432`). |

Otras variables:

| Variable | Descripción |
|---|---|
| `DEBUG` | `True` en desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma. |
| `TIME_ZONE` | Zona horaria (`America/La_Paz` por defecto). |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos del frontend. |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Duración del access token. |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Duración del refresh token. |
| `LOGIN_THROTTLE_RATE` | Límite de intentos de login (por defecto `5/min`). |
| `ADMIN_SISTEMA_USERNAME` | Usuario del administrador inicial de la semilla. |
| `ADMIN_SISTEMA_EMAIL` | Email del administrador inicial. |
| `ADMIN_SISTEMA_PASSWORD` | Contraseña del administrador inicial (solo se usa al crearlo). |
| `SEED_CREAR_CLINICA_DEMO` | Si es `True`, crea una clínica demo cuando no existe ninguna. |
| `SEED_CLINICA_DEMO_NIT` | NIT de la clínica demo. |
| `SEED_CLINICA_DEMO_NOMBRE` | Nombre de la clínica demo. |

> `backend/.env` está en `.gitignore`. Nunca subas secretos al repositorio.
> La base de datos debe existir vacía; Django crea las tablas con `migrate`.

### 3. Aplicar migraciones

```bash
python manage.py migrate
```

### 4. Cargar datos semilla

```bash
python manage.py cargar_semilla
```

El comando es idempotente: se puede ejecutar varias veces sin duplicar registros.
Carga planes de suscripción, roles base y especialidades por clínica, y el
administrador del sistema definido en `.env`.

### 5. API del Sprint 1

Base: `/api/v1/`. Autenticación con `Authorization: Bearer <access>`.

| Grupo | Rutas principales |
|---|---|
| Autenticación | `/auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/me/`, `/auth/cambiar-password/` |
| Clínicas y planes | `/clinicas/`, `/planes/` |
| Suscripciones | `/suscripciones/`, `/{id}/renovar/`, `/{id}/cambiar-plan/`, `/{id}/cancelar/` |
| Seguridad | `/usuarios/`, `/roles/`, `/usuario-roles/` |
| Personal | `/personal/`, `/personal/{id}/vincular-usuario/`, `/especialidades/`, `/medicos/`, `/horarios/` |

Reglas clave:

- Un Administrador de clínica sin suscripción vigente entra en **modo restringido**:
  solo accede a `/auth/me/`, `GET /planes/` y sus endpoints de suscripción. El resto
  responde `403` con código `suscripcion_vencida`.
- El primer administrador creado junto con una clínica no valida `max_usuarios` ni
  suscripción (bootstrap). La creación normal de usuarios sin suscripción se rechaza.
- La creación y reactivación de usuarios respeta `max_usuarios` con bloqueo de fila;
  en concurrencia, exactamente una petición crea el usuario y la otra recibe
  `409 limite_usuarios`.
- Los roles base no se renombran, desactivan ni eliminan; solo se edita su descripción.
- La clínica nunca se toma del cuerpo de la petición.

Formato uniforme de error:

```json
{
  "codigo": "suscripcion_vencida",
  "mensaje": "La clínica no tiene una suscripción vigente.",
  "detalles": {}
}
```

El catálogo completo de códigos está en
[`docs/INFORME_SPRINT1.md`](docs/INFORME_SPRINT1.md) y en la descripción de
`/api/docs/`, donde el botón **Authorize** permite pegar el access token JWT.

### 6. Ejecutar el servidor

```bash
python manage.py runserver
```

- Raíz (redirige a la documentación): <http://localhost:8000/>
- Salud del backend (sin sesión): <http://localhost:8000/api/health/>
- Admin de Django: <http://localhost:8000/admin/>
- Documentación OpenAPI: <http://localhost:8000/api/docs/>
- Esquema OpenAPI: <http://localhost:8000/api/schema/>

### 7. Ejecutar pruebas

Con `backend/.env` configurado y PostgreSQL disponible:

```bash
pytest
```

La configuración de pruebas usa `config.settings_test` (hash de contraseñas rápido
solo para tests). Para ejecutar solo una parte de la suite:

```bash
pytest tests/test_tenant.py -v
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Documentación

- [`docs/arquitectura.md`](docs/arquitectura.md): stack, capas, estrategia multitenant y API del Sprint 1.
- [`docs/modelo_fisico.md`](docs/modelo_fisico.md): tablas, tipos, claves, índices y ER.
- [`docs/INFORME_SPRINT0.md`](docs/INFORME_SPRINT0.md): cierre del Sprint 0.
- [`docs/INFORME_SPRINT1.md`](docs/INFORME_SPRINT1.md): cierre del Sprint 1 y catálogo de errores.
- [`docs/DoR_DoD.md`](docs/DoR_DoD.md): Definition of Ready y Definition of Done.

## Integración continua

`.github/workflows/ci.yml` se ejecuta en cada push y pull request:

1. Levanta un servicio PostgreSQL 17.
2. Instala las dependencias de `requirements.txt`.
3. Comprueba que no haya migraciones pendientes.
4. Aplica las migraciones.
5. Ejecuta `pytest`.

Las credenciales del CI son valores de prueba definidos en el propio workflow,
nunca secretos reales.
