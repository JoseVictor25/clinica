# Despliegue en AWS EC2

Esta configuracion ejecuta React, Django, PostgreSQL y Caddy en una sola instancia
EC2. Solo Caddy publica puertos. PostgreSQL y Gunicorn permanecen en redes privadas
de Docker. Caddy obtiene y renueva certificados TLS automaticamente cuando se usa
un dominio.

Ollama puede correr en una segunda EC2 privada; consulta [ollama-ec2.md](ollama-ec2.md).
La app Flutter se distribuye separadamente desde Google Play; consulta
[app-movil-play.md](app-movil-play.md).

## 1. Crear la instancia

Configuracion recomendada para una entrega o entorno pequeno:

- Ubuntu Server 24.04 LTS, arquitectura `x86_64`.
- `t3.small` como minimo (2 GiB RAM); `t3.medium` si se espera mas carga.
- Volumen EBS `gp3` de al menos 20 GiB con borrado al terminar desactivado si se
  quiere conservar la base al reemplazar la instancia.
- Elastic IP para que la direccion publica no cambie.

En el Security Group permita:

| Puerto | Origen | Uso |
|---|---|---|
| 22/TCP | Su IP publica `/32` | SSH |
| 80/TCP | `0.0.0.0/0` y `::/0` | HTTP y validacion de certificados |
| 443/TCP | `0.0.0.0/0` y `::/0` | HTTPS |
| 443/UDP | `0.0.0.0/0` y `::/0` | HTTP/3 opcional |

No abra 5432, 8000, 8080 ni 5173.

## 2. Instalar Docker

Conectese por SSH, clone el repositorio y ejecute:

```bash
cd clinica
chmod +x deploy/ec2/*.sh
sudo ./deploy/ec2/bootstrap-ubuntu.sh
```

Cierre la sesion SSH y vuelva a entrar para aplicar la pertenencia al grupo
`docker`.

## 3. Configurar variables

```bash
cp .env.ec2.example .env.ec2
chmod 600 .env.ec2
openssl rand -base64 48
```

Edite `.env.ec2`; use la salida de `openssl` como `SECRET_KEY` y genere
contrasenas distintas para PostgreSQL y el administrador.

### Inicio por IP publica

Para comprobar primero el servidor sin dominio:

```dotenv
SITE_ADDRESS=:80
ALLOWED_HOSTS=IP_PUBLICA,localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=http://IP_PUBLICA
CORS_ALLOWED_ORIGINS=http://IP_PUBLICA
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
```

### Dominio y HTTPS

Cree un registro DNS `A` que apunte el dominio a la Elastic IP. Cuando haya
propagado, cambie:

```dotenv
SITE_ADDRESS=clinica.ejemplo.com
ALLOWED_HOSTS=clinica.ejemplo.com,localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=https://clinica.ejemplo.com
CORS_ALLOWED_ORIGINS=https://clinica.ejemplo.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

No incluya rutas ni una barra final en los origenes. Si se usan varios hosts u
origenes, separe los valores con comas. Active HSTS solo despues de comprobar
que el dominio funciona correctamente por HTTPS. Mantenga
`SECURE_HSTS_INCLUDE_SUBDOMAINS` y `SECURE_HSTS_PRELOAD` en `False` salvo que
todos los subdominios usen HTTPS y haya evaluado el registro preload.

## 4. Desplegar

```bash
./deploy/ec2/deploy.sh
```

El despliegue valida Compose, construye las imagenes, espera PostgreSQL, aplica
migraciones, recoge archivos estaticos y levanta la aplicacion. Compruebe:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yaml ps
curl -I "http://127.0.0.1/api/health/"
```

Con dominio y HTTPS, cambie la URL del segundo comando por la URL publica.

La semilla es manual para evitar crear datos demo accidentalmente:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yaml --profile tools run --rm seed
```

## 5. Actualizar

```bash
git pull --ff-only
./deploy/ec2/deploy.sh
```

Las migraciones se ejecutan antes de reemplazar el backend. El volumen
`postgres_data` conserva la base entre despliegues.

## 6. Registros y diagnostico

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yaml ps
docker compose --env-file .env.ec2 -f compose.ec2.yaml logs --tail=200 backend
docker compose --env-file .env.ec2 -f compose.ec2.yaml logs --tail=200 proxy
docker compose --env-file .env.ec2 -f compose.ec2.yaml exec backend python manage.py check --deploy
```

## 7. Respaldo y restauracion

Antes de una actualizacion importante, cree un respaldo fuera del volumen:

```bash
mkdir -p backups
docker compose --env-file .env.ec2 -f compose.ec2.yaml exec -T db \
  pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "backups/clinica-$(date +%F-%H%M).sql.gz"
```

Las variables del comando deben estar cargadas en la sesion (`set -a; source
.env.ec2; set +a`). Copie los respaldos periodicamente a S3 o a otro equipo; un
respaldo guardado solo en la misma instancia no protege contra perdida del EBS.

Para restaurar, detenga primero `backend`, confirme que la base destino sea la
correcta y use `psql`. La restauracion reemplaza datos y debe ensayarse antes de
usarla en produccion.
