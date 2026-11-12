"""Genera el inventario, el documento de código completo y el ZIP de entrega."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

entrega = Path(__file__).resolve().parent
proyecto = entrega.parent
fuentes = sorted((entrega / 'frontend' / 'src').rglob('*'))
cambios = []
for archivo in fuentes:
    if not archivo.is_file():
        continue
    relativa = archivo.relative_to(entrega)
    original = proyecto / relativa
    if not original.exists():
        cambios.append(('CREAR', relativa, archivo))
    elif archivo.read_bytes() != original.read_bytes():
        cambios.append(('REEMPLAZAR', relativa, archivo))

guia = '''# Entrega completa del frontend

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
'''
for accion, relativa, _ in cambios:
    guia += f'| {accion} | `{relativa.as_posix()}` |\n'
guia += '''
## Ejecutar al terminar

En una terminal, desde la raíz del proyecto:

```powershell
cd backend
.\\venv\\Scripts\\python.exe manage.py runserver
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
'''
(entrega / 'LEEME.md').write_text(guia, encoding='utf-8')

import csv
with (entrega / 'ARCHIVOS.csv').open('w', newline='', encoding='utf-8-sig') as salida:
    escritor = csv.writer(salida)
    escritor.writerow(['Accion', 'Ruta'])
    for accion, relativa, _ in cambios:
        escritor.writerow([accion, relativa.as_posix()])

codigo = '# Código completo por archivo\n\n'
codigo += 'Las rutas son destinos en el proyecto original. Copia el bloque entero de cada archivo. No elimines archivos.\n\n'
for accion, relativa, archivo in cambios:
    codigo += f'## {accion}: {relativa.as_posix()}\n\n```{archivo.suffix.lstrip(".")}\n'
    codigo += archivo.read_text(encoding='utf-8-sig').rstrip() + '\n```\n\n'
(entrega / 'CODIGO_COMPLETO.md').write_text(codigo, encoding='utf-8')

destino_zip = proyecto / 'entrega_frontend_completo.zip'
with ZipFile(destino_zip, 'w', ZIP_DEFLATED) as paquete:
    for nombre in ['LEEME.md', 'CODIGO_COMPLETO.md', 'COBERTURA.md', 'ARCHIVOS.csv']:
        paquete.write(entrega / nombre, f'entrega_frontend_completo/{nombre}')
    for archivo in (entrega / 'frontend' / 'src').rglob('*'):
        if archivo.is_file():
            paquete.write(archivo, f'entrega_frontend_completo/{archivo.relative_to(entrega).as_posix()}')
    for nombre in ['package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html', '.env.example']:
        archivo = entrega / 'frontend' / nombre
        if archivo.exists():
            paquete.write(archivo, f'entrega_frontend_completo/frontend/{nombre}')
    for archivo in (entrega / 'frontend' / 'public').rglob('*'):
        if archivo.is_file():
            paquete.write(archivo, f'entrega_frontend_completo/{archivo.relative_to(entrega).as_posix()}')

print(f'{len(cambios)} archivos nuevos o modificados en el inventario.')
print(f'ZIP: {destino_zip.name} ({destino_zip.stat().st_size} bytes).')
