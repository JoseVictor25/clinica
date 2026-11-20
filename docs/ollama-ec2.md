# Ollama en una instancia EC2 privada

`deploy/ollama/ollama-ec2.yaml` crea una instancia Ubuntu con Ollama y el modelo
configurado. No crea ni modifica la EC2 de la clínica; ambas deben estar en la
misma VPC. Ollama no recibe una IP pública y la API 11434 solo acepta conexiones
desde el Security Group del backend. No se abre SSH; la administración se hace
por Systems Manager Session Manager. La subred privada debe tener una ruta NAT
para descargar Ollama y el modelo durante el arranque y para que SSM conecte.

## Crear la instancia

En CloudFormation, crea un stack a partir de `deploy/ollama/ollama-ec2.yaml` y
completa estos parámetros:

- `VpcId`: la VPC donde vive la EC2 de la clínica.
- `SubnetId`: una subred con salida a Internet/NAT.
- `BackendSecurityGroupId`: el Security Group adjunto a la EC2 de la clínica.
- `InstanceType`: `m7i.xlarge` como punto de partida CPU, `m7i.2xlarge` para más
  capacidad o `g6.xlarge` si está disponible en la región y se necesita GPU.
- `OllamaModel`: por defecto `qwen2.5:7b`.

El stack conserva el volumen EBS al borrar la instancia; al eliminar el stack,
el volumen puede seguir generando costo hasta borrarlo explícitamente. Revisa la
estimación de AWS para tu región y detén o elimina la instancia cuando no la
uses. La capacidad real depende de concurrencia y tiempos esperados; mide con
consultas representativas antes de abrir el servicio a usuarios.

Al completar, copia el output `BaseUrl` a `.env.ec2` en la instancia de la
clínica:

```dotenv
OLLAMA_BASE_URL=http://IP_PRIVADA_OLLAMA:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=180
```

Luego reinicia el backend de la clínica:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yaml up -d --force-recreate backend
```

Ollama está en una red privada, pero su endpoint no cifra el tráfico ni exige
autenticación por defecto. Manténlo dentro de la VPC, limita su Security Group
al backend, y no coloques allí datos clínicos identificables. El móvil debe
llamar solo a la API HTTPS de la clínica, nunca a Ollama directamente.

## Diagnóstico

En Ollama, usa Session Manager y ejecuta `systemctl status ollama` y
`ollama list`. En la instancia de clínica, valida la conexión privada con
`curl http://IP_PRIVADA_OLLAMA:11434/api/tags` y revisa los logs del backend.
La app devuelve servicio no disponible cuando Ollama no responde o excede el
timeout.
