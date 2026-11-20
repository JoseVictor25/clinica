# Docker: desarrollo y produccion

El proyecto usa PostgreSQL 17, Django REST Framework y React/Vite. No necesita
Redis porque actualmente no utiliza Channels, Celery ni WebSockets.

## Desarrollo

1. Cree el archivo local de variables:

```powershell
Copy-Item .env.docker.example .env.docker
```

2. Edite `.env.docker` y cambie como minimo `SECRET_KEY`, `DB_PASSWORD` y
   `ADMIN_SISTEMA_PASSWORD`. El archivo esta ignorado por Git.

3. Construya e inicie los servicios:

```powershell
docker compose --env-file .env.docker up --build
```

Compose espera que PostgreSQL este saludable, ejecuta las migraciones y luego
inicia backend y frontend. Las direcciones predeterminadas son:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- Salud: <http://localhost:8000/api/health/>
- Swagger: <http://localhost:8000/api/docs/>
- PostgreSQL desde el host: `localhost:5433`

La base se inicializa con intercalacion ICU `es-BO` para que busquedas y orden
alfabetico sean consistentes con los datos en espanol. Los datos quedan en el volumen `postgres_data`. El codigo del backend y
frontend esta montado para permitir recarga durante el desarrollo.

### Cargar la semilla

La semilla es explicita para no modificar datos automaticamente en cada inicio:

```powershell
docker compose --env-file .env.docker --profile tools run --rm seed
```

### Ejecutar pruebas del backend

```powershell
docker compose --env-file .env.docker --profile tools run --rm test-backend
```

### Detener los contenedores

```powershell
docker compose --env-file .env.docker down
```

Para borrar tambien la base de datos local, use `down --volumes` solamente
cuando quiera eliminar todos sus datos.

## Produccion local o servidor

Use `compose.prod.yaml`. Antes de iniciar, configure en `.env.docker`:

```dotenv
DEBUG=False
ALLOWED_HOSTS=su-dominio.com
CORS_ALLOWED_ORIGINS=https://su-dominio.com
CSRF_TRUSTED_ORIGINS=https://su-dominio.com
TRUST_PROXY_HEADERS=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Si prueba produccion sin HTTPS en `localhost:8080`, mantenga las cuatro opciones
`SECURE_*`/cookies en `False` y use `http://localhost:8080` como origen confiable.

Inicie la aplicacion:

```powershell
docker compose --env-file .env.docker -f compose.prod.yaml up --build -d
```

La aplicacion completa queda en <http://localhost:8080>. Nginx sirve React y
envia `/api/`, `/admin/` y `/static/` al backend. PostgreSQL no publica ningun
puerto en esta configuracion.

Para cargar la semilla de forma controlada:

```powershell
docker compose --env-file .env.docker -f compose.prod.yaml --profile tools run --rm seed
```

## Operaciones utiles

```powershell
# Estado y salud
docker compose --env-file .env.docker ps

# Registros de todos los servicios
docker compose --env-file .env.docker logs -f

# Registros del backend
docker compose --env-file .env.docker logs -f backend

# Ejecutar un comando Django
docker compose --env-file .env.docker exec backend python manage.py check

# Crear un respaldo SQL
docker compose --env-file .env.docker exec -T db pg_dump -U clinicas clinicas_db > respaldo.sql
```

Los valores `clinicas` y `clinicas_db` del respaldo deben coincidir con
`DB_USER` y `DB_NAME` de `.env.docker`.

## Servicios y responsabilidades

| Servicio | Desarrollo | Produccion |
|---|---|---|
| `db` | PostgreSQL con puerto opcional al host | PostgreSQL solo en red interna |
| `migrate` | Aplica migraciones y termina | Aplica migraciones y termina |
| `backend` | `runserver` con codigo montado | Gunicorn, WhiteNoise y usuario sin privilegios |
| `frontend` | Vite con recarga | Build estatico servido por Nginx |
| `reminders` | Recordatorios de citas y push | Recordatorios de citas y push |
| `proxy` | No incluido | Caddy con HTTPS automatico en EC2 |
| `seed` | Herramienta opcional | Herramienta opcional |
| `test-backend` | Suite pytest opcional | No se incluye |

Ollama no se instala como servicio de este Compose de produccion. Para ejecutarlo
en una instancia privada independiente, sigue [ollama-ec2.md](ollama-ec2.md).
La app movil tampoco se sirve desde EC2: el proceso de firma y distribucion de
Flutter para Play esta en [app-movil-play.md](app-movil-play.md).
