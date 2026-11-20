# App Flutter para prueba en Google Play

La app Flutter se distribuye como Android App Bundle desde Play Console. No se incluye en EC2: el telefono instala la app desde la pista de prueba y consume la API de la clinica mediante HTTPS.

## Conexion a produccion

La direccion compartida actualmente (`http://3.81.167.202`) no es apta para una version de Play: usa HTTP y no tiene un nombre de dominio con certificado TLS. Primero configura un dominio (por ejemplo `api.tu-dominio.com`), apunta su DNS al servidor y habilita HTTPS con un certificado valido en Caddy. La web y el movil deben consumir el mismo backend publico.

El script de publicacion recibe la URL de la API en tiempo de compilacion, para que el AAB no herede accidentalmente las direcciones locales de `.env`:

```powershell
cd frontend_flutter
.\build-play.ps1 -ApiBaseUrl "https://api.tu-dominio.com/api/v1/"
```

Como alternativa para desarrollo, copia `.env.example` como `.env` y configura:

```dotenv
API_BASE_URL=https://api.tu-dominio.com/api/v1/
API_BASE_URL_ANDROID=https://api.tu-dominio.com/api/v1/
FIREBASE_ENABLED=true
```

No uses `localhost`, `10.0.2.2` ni la direccion privada de Ollama en la app. Nunca guardes claves privadas en `.env` del cliente.

Para push, coloca el `google-services.json` de la app Android `com.clinica.frontend_flutter` en `android/app/`. El proyecto Firebase debe coincidir con el JSON de cuenta de servicio que usa el backend. El archivo no se versiona.

## Firma de Play

1. Crea una clave de subida privada y respalda la clave en un lugar seguro:

   ```powershell
   keytool -genkey -v -keystore "$env:USERPROFILE\upload-keystore.jks" -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```

2. Copia `android/key.properties.example` a `android/key.properties`, completa las contrasenas y cambia `storeFile` a la ruta absoluta de tu keystore. Ambos archivos reales estan excluidos de Git. No pierdas el keystore ni sus contrasenas.
3. En `pubspec.yaml`, incrementa el numero despues de `+` en `version`, por ejemplo `1.0.0+2`, en cada carga nueva.
4. Comprueba que `targetSdk` sea el nivel exigido por Google Play. Ahora el proyecto fija API 36.
5. Ejecuta `./build-play.ps1 -ApiBaseUrl "https://api.tu-dominio.com/api/v1/"`. El script valida HTTPS, el dominio y la clave de subida, y genera el AAB. Para hacerlo manualmente:

   ```powershell
   flutter pub get
   flutter test
   flutter build appbundle --release `
     --dart-define=API_BASE_URL=https://api.tu-dominio.com/api/v1/ `
     --dart-define=API_BASE_URL_ANDROID=https://api.tu-dominio.com/api/v1/
   ```

El artefacto queda en `build/app/outputs/bundle/release/app-release.aab`. El nombre que se muestra al instalar es **Clinica** y el icono Android es el de la clinica. El ID Android permanece `com.clinica.frontend_flutter` para conservar la identidad Firebase; el titulo de la ficha de Play Console se configura aparte. Sube el bundle a una pista interna o cerrada en Play Console, agrega testers y comparte el enlace. Play App Signing se configura en Play Console al crear la app.

## Firebase Cloud Messaging

Ademas de `FIREBASE_ENABLED=true` para el build movil, en EC2 configura `FCM_ENABLED=True` y deja la cuenta de servicio fuera del repositorio en `backend/secrets/firebase-admin.json` (el compose la monta como solo lectura). El usuario debe iniciar sesion en la app y aceptar permisos para registrar su dispositivo. Para requisitos de Firebase y diagnostico, consulta `notificaciones-push-firebase.md`.
