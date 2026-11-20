# Videollamadas de telemedicina

La aplicación crea salas de Daily.co para las citas con modalidad `VIRTUAL`. La
misma cita entrega el enlace al médico y al paciente que están asociados a ella.

## Configurar Daily.co

1. Crea una cuenta de Daily.co y genera una API key desde el panel del servicio.
2. Guarda la clave únicamente en el entorno del backend:

   ```dotenv
   DAILY_API_KEY=
   DAILY_API_BASE_URL=https://api.daily.co/v1
   ```

   En desarrollo local, usa `backend/.env`; en EC2, usa el archivo de entorno
   privado del despliegue. No pongas esta clave en `frontend_flutter/.env`, en
   React ni en Git.
3. Reinicia el backend. Al crear una cita virtual, el backend solicita una sala
   a Daily y guarda su enlace en la cita. Las citas presenciales no crean sala.

Si `DAILY_API_KEY` está vacía o Daily rechaza la solicitud, el backend no puede
crear la cita virtual y devuelve un error de telemedicina no configurada o de
servicio externo.

## Entrar a la videollamada

- **Médico en web:** abre **Mi agenda**, selecciona la cita virtual y pulsa
  **Abrir sala virtual**.
- **Paciente en web:** abre sus citas y pulsa **Ingresar a la sala virtual**.
- **Médico en Flutter:** abre **Agenda**, selecciona la cita y pulsa
  **Abrir sala virtual**.
- **Paciente en Flutter:** abre **Agenda/Citas**, entra al detalle de su cita y
  pulsa **Ingresar a sala virtual**.

En Flutter, el enlace se abre en el navegador instalado en el teléfono; la
videollamada no está embebida en la interfaz nativa de la app. El médico y el
paciente deben abrir el enlace de la misma cita y permitir al navegador usar la
cámara y el micrófono. En web, la sala se muestra dentro de la aplicación.

## Privacidad de las salas

La implementación actual crea salas `public` de Daily. El acceso depende de
conocer el enlace y la API limita la entrega de datos de la cita al paciente o
médico asociado, pero el enlace de Daily puede compartirse fuera de la app. Para
un entorno clínico de producción, se recomienda cambiar las salas a privadas y
emitir tokens de reunión de corta duración para los participantes autorizados.
