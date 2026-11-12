# Entrega completa del frontend

El código está preparado en esta carpeta separada. No se ha reemplazado tu frontend original.

## Cómo aplicarlo

1. Las rutas del inventario son relativas a la raíz de `clinica`.
2. Para cada archivo marcado CREAR, crea sus carpetas y copia el contenido completo.
3. Para cada archivo marcado REEMPLAZAR, sustituye todo su contenido.
4. No elimines archivos. Conserva `Raiz.tsx`; contiene el proveedor de autenticación.
5. Conserva tu `frontend/.env`, dependencias y configuración actuales.
6. Respeta `Personal` con P mayúscula: esa es la carpeta existente en tu proyecto y el router la importa así.

El documento CODIGO_COMPLETO.md incluye los bloques completos de cada archivo nuevo o cambiado.
La carpeta frontend/src también contiene una copia completa del código fuente, incluidos los archivos previos.
El ZIP contiene las fuentes y configuración, pero no secretos, node_modules ni compilados.

Puedes aplicar todos los archivos del inventario desde PowerShell, situado en la raíz de clinica:

```powershell
$taskDelivery = Join-Path (Get-Location) 'entrega_frontend_completo'
$taskManifest = Import-Csv -LiteralPath (Join-Path $taskDelivery 'ARCHIVOS.csv')
foreach ($taskEntry in $taskManifest) {
    $taskSource = Join-Path $taskDelivery $taskEntry.Ruta
    $taskDestination = Join-Path (Get-Location) $taskEntry.Ruta
    $taskParent = Split-Path -Parent $taskDestination
    New-Item -ItemType Directory -Path $taskParent -Force | Out-Null
    Copy-Item -LiteralPath $taskSource -Destination $taskDestination -Force
}
```

Este comando reemplaza solamente los archivos enumerados abajo, sin borrar archivos.
También puedes copiarlos manualmente desde frontend/src.

## Archivos

| Acción | Ruta de destino |
|---|---|
| REEMPLAZAR | `frontend/src/api/client.ts` |
| CREAR | `frontend/src/api/modules/gestion.ts` |
| CREAR | `frontend/src/components/gestion/GestionRecurso.tsx` |
| REEMPLAZAR | `frontend/src/components/ui/Modal.tsx` |
| REEMPLAZAR | `frontend/src/lib/navigation.ts` |
| REEMPLAZAR | `frontend/src/pages/clinica/especialidades/EspecialidadesPage.tsx` |
| CREAR | `frontend/src/pages/clinica/horarios/HorariosPage.tsx` |
| CREAR | `frontend/src/pages/clinica/medicos/MedicosPage.tsx` |
| CREAR | `frontend/src/pages/clinica/MiClinicaPage.tsx` |
| CREAR | `frontend/src/pages/clinica/suscripciones/SuscripcionDetalleModal.tsx` |
| REEMPLAZAR | `frontend/src/pages/clinica/suscripciones/SuscripcionesPage.tsx` |
| CREAR | `frontend/src/pages/cuenta/CuentaPage.tsx` |
| CREAR | `frontend/src/pages/sistema/ClinicasPage.tsx` |
| CREAR | `frontend/src/pages/sistema/PlanesPage.tsx` |
| REEMPLAZAR | `frontend/src/routes/ProtectedRoute.tsx` |
| REEMPLAZAR | `frontend/src/routes/Raiz.tsx` |
| REEMPLAZAR | `frontend/src/routes/router.tsx` |

## Ejecutar al terminar

En una terminal, desde la raíz del proyecto:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver
```

En otra terminal, desde la raíz del proyecto:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
npm.cmd run dev
```

Si falta frontend/.env, crea ese archivo con:

```dotenv
VITE_API_URL=http://localhost:8000/api/v1/
```

Las comprobaciones de compilación se ejecutaron sobre la copia de entrega; las
pruebas manuales contra el backend quedan para el final, como pediste.
Consulta COBERTURA.md para el alcance exacto y la lista de pruebas funcionales.
