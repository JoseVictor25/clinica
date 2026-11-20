# App móvil de Clínica

Cliente Flutter independiente del frontend web. Incluye inicio de sesión JWT y las pantallas actuales de los roles Médico y Paciente, conectadas a los endpoints existentes de Django.

## Configurar la API

1. Desde `frontend_flutter`, crea tu archivo local de entorno:

   ```powershell
   Copy-Item .env.example .env
   ```

2. `API_BASE_URL` apunta al backend desde Chrome y el simulador de iOS; `API_BASE_URL_ANDROID` usa `10.0.2.2` para el emulador Android. Ajusta el puerto al valor de `BACKEND_PORT_EXTERNAL` en `.env.docker`. En un teléfono físico, reemplaza la URL Android por la IP local de la computadora donde corre Django.
3. Inicia Django desde `backend` para que acepte conexiones del emulador:

   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

   `.env.docker` incluye `10.0.2.2` en `ALLOWED_HOSTS`. Para un teléfono físico, agrega también la IP o el nombre de host que el dispositivo use para acceder a Django. El firewall debe permitir la conexión al puerto publicado por Docker.

## Ejecutar

```powershell
flutter pub get
flutter run
```

Con un emulador Android activo, Flutter lo selecciona como destino. Para usar Chrome ejecuta `flutter run -d chrome --web-port=5174`. Django permite ese origen en `CORS_ALLOWED_ORIGINS`.

## Funciones portadas

- **Paciente:** datos personales, historia clínica con enfermedades y alergias, citas con filtros por estado, consultas, estudios asociados y detalle de recetas.
- **Médico:** agenda por fecha y estado, historia de consultas del paciente, registro de consulta desde una cita confirmada, detalle de consulta, emisión de recetas con uno o varios medicamentos y consulta de advertencias por alergias.
- **Sesión:** login, renovación JWT al recibir 401, almacenamiento seguro de tokens y cierre de sesión.

El backend valida los roles y la propiedad de cada dato; la app solo muestra las opciones correspondientes al perfil autenticado.

## Organización del código

- `lib/core/`: configuración, cliente HTTP, paginación, tokens y sesión.
- `lib/features/auth/`: inicio de sesión.
- `lib/features/patient/`: API y pantallas del portal del paciente.
- `lib/features/doctor/`: agenda, historial, consultas y recetas.

Las dependencias principales son Dio, Riverpod, GoRouter, Flutter Secure Storage, `flutter_dotenv`, `intl` y `url_launcher`. También están instalados Firebase Core y Firebase Messaging; FCM aún necesita el proyecto y archivos de configuración de Firebase antes de activar notificaciones push.
