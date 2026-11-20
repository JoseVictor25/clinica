# Notificaciones push con Firebase Cloud Messaging

La app Flutter ya tiene los paquetes `firebase_core` y `firebase_messaging`. El backend guarda el ID de instalación FCM asociado a una cuenta y envía avisos genéricos para citas registradas, confirmadas, canceladas o reprogramadas. Las notificaciones no incluyen diagnóstico ni otros datos clínicos.

## Configurar Firebase

1. En Firebase Console, crea un proyecto y agrega una app Android con el ID de paquete `com.clinica.frontend_flutter`.
2. Desde `frontend_flutter/`, ejecuta `flutterfire configure` y selecciona el proyecto y Android. Si también usarás iOS, selecciónalo en el mismo paso. La configuración de Web requiere configurar también VAPID y el service worker; este primer flujo usa Android/iOS.
3. En el backend, crea una cuenta de servicio con permiso para enviar mensajes de Firebase Cloud Messaging y descarga su JSON privado. Guárdalo en `backend/secrets/firebase-admin.json`. Esa carpeta está excluida de Git y Compose la monta como solo lectura.
4. En `.env.docker`, agrega `FCM_ENABLED=True`. Compose ya apunta `FCM_SERVICE_ACCOUNT_FILE` a `/run/secrets/firebase/firebase-admin.json`; no copies ese JSON al repositorio.
5. En `frontend_flutter/.env`, agrega `FIREBASE_ENABLED=true`.
6. Reconstruye/inicia el backend para instalar Firebase Admin SDK y aplicar la migración. Reconstruye Flutter con `flutter run` en un dispositivo Android con Google Play Services.

La app solicita permiso de notificaciones después del inicio de sesión, registra el ID de instalación en Django y lo elimina al cerrar sesión. En Android 13 o posterior se debe aceptar el permiso del sistema. Para iOS además hay que subir una clave APNs a Firebase y activar Push Notifications/Background Modes en Xcode.

## Endpoints y eventos

- `POST /api/v1/notificaciones/dispositivos/` registra o actualiza `{ "token": "...", "plataforma": "ANDROID" }`.
- `DELETE /api/v1/notificaciones/dispositivos/` elimina el dispositivo de la cuenta autenticada con el mismo cuerpo.
- Las acciones de crear, confirmar, cancelar y reprogramar una cita avisan al paciente vinculado y al médico cuando tienen un dispositivo registrado.

Con `FCM_ENABLED=False`, la API sigue permitiendo registrar dispositivos, pero Django no intenta enviar mensajes. La configuración de Firebase no se activa hasta añadir credenciales válidas.

## Recordatorios automáticos

Los servicios `reminders` de `compose.yaml`, `compose.prod.yaml` y `compose.ec2.yaml` revisan cada minuto las citas activas y envían al paciente vinculado un recordatorio alrededor de dos horas antes. El envío queda en la bandeja aunque el dispositivo esté desconectado; para recibirlo como push, el paciente necesita una cuenta vinculada y un dispositivo FCM registrado. Para revisar el proceso, usa `docker compose logs -f reminders`.

El portal de paciente actualmente permite consultar citas; su registro lo realizan administración o recepción. Si la recepción crea una ficha sin vincular una cuenta, todavía no existe un usuario/app a quien enviar notificaciones. La cuenta se crea o vincula desde la ficha del paciente y el paciente debe iniciar sesión para registrar su dispositivo.
