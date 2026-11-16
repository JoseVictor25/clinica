#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import time

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
for intento in range(1, 31):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"PostgreSQL disponible en {host}:{port}")
            break
    except OSError:
        if intento == 30:
            raise SystemExit(f"PostgreSQL no respondio en {host}:{port}")
        print(f"Esperando PostgreSQL ({intento}/30)...")
        time.sleep(2)
PY

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
