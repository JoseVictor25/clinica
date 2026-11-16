# Demostración del Sprint 2

Esta guía recorre el flujo clínico completo con datos ficticios en un entorno local. No use información clínica real ni ejecute estos pasos contra producción.

## 1. Requisitos

- PostgreSQL local configurado para el proyecto.
- Entorno virtual existente en `backend/venv`.
- Dependencias del frontend instaladas en `frontend/node_modules`.
- Variables locales requeridas presentes en `backend/.env`; no copie sus valores en documentación o capturas.
- Migraciones aplicadas y clínica de demostración con suscripción vigente.

## 2. Iniciar el proyecto

Desde la raíz del repositorio, abra dos terminales de PowerShell.

Backend:

```powershell
$env:DEBUG = "True"
.\backend\venv\Scripts\python.exe backend\manage.py migrate
.\backend\venv\Scripts\python.exe backend\manage.py runserver
```

Frontend:

```powershell
Set-Location frontend
npm.cmd run dev
```

Abra `http://localhost:5173/`. La API queda disponible en `http://127.0.0.1:8000/api/v1/`.

Para comprobar automáticamente el recorrido antes de la demostración:

```powershell
Set-Location backend
$env:DEBUG = "True"
.\venv\Scripts\python.exe -m pytest tests\api\sprint2\test_flujo_completo_sprint2.py -v -p no:cacheprovider
```

La prueba usa una base aislada de pytest y elimina sus datos al finalizar.

## 3. Preparar datos ficticios

Use los mecanismos administrativos existentes de la aplicación. No agregue datos directamente a producción.

1. Disponga de una clínica activa con suscripción vigente.
2. Cree cuentas ficticias con estos roles:
   - Administrador de clínica.
   - Recepcionista.
   - Médico.
   - Paciente.
3. Desde **Personal**, cree el registro del profesional y vincúlelo con la cuenta que tiene rol Médico.
4. Desde **Médicos**, complete especialidad y colegiatura.
5. Desde **Horarios**, agregue un bloque futuro para ese médico.
6. Mantenga inicialmente la cuenta Paciente sin vincular; se vinculará durante el recorrido.

Defina las contraseñas localmente. Esta guía no contiene credenciales reutilizables.

## 4. Recorrido principal

### Recepción: paciente y cita

1. Inicie sesión como Recepcionista.
2. Abra **Pacientes** y seleccione **Registrar paciente**.
3. Complete datos ficticios y guarde.
4. Resultado esperado: el paciente aparece activo. El backend crea exactamente una historia clínica en la misma transacción.
5. Abra **Citas** y seleccione una especialidad, médico, paciente y fecha futura.
6. Elija uno de los horarios ofrecidos y registre la cita.
7. Resultado esperado: la cita queda `PROGRAMADA` y el bloque deja de aparecer como disponible.
8. Confirme la cita.
9. Resultado esperado: la cita queda `CONFIRMADA`.

Para demostrar estados alternativos, use citas separadas:

- Reprograme una cita programada hacia otro bloque disponible; debe volver a `PROGRAMADA` y liberar el bloque anterior.
- Cancele otra cita programada o confirmada; debe quedar `CANCELADA` y liberar su bloque.
- Una cita `ATENDIDA` debe rechazar cancelación y reprogramación.

### Médico: antecedentes, consulta y receta

1. Cierre sesión e ingrese como Médico.
2. Abra **Pacientes**, consulte el paciente y registre:
   - Una enfermedad ficticia.
   - Una alergia de tipo `MEDICAMENTO`, por ejemplo con el mismo nombre que se usará después en la receta.
3. Abra **Mi agenda**.
4. Resultado esperado: aparece únicamente la cita asignada al médico autenticado.
5. Atienda la cita confirmada y registre motivo, observación y diagnóstico.
6. Resultado esperado: se crea una sola consulta y la cita cambia a `ATENDIDA`.
7. Emita una receta con al menos dos medicamentos. Uno debe coincidir con la alergia MEDICAMENTO registrada.
8. Resultado esperado:
   - La receta conserva el orden de los medicamentos.
   - La coincidencia genera una advertencia informativa.
   - La advertencia no impide emitir la receta.
9. Abra el historial del paciente.
10. Resultado esperado: se muestran cronológicamente consulta, cita, diagnóstico, receta y medicamentos.

### Administración: vincular cuenta

1. Cierre sesión e ingrese como Administrador de clínica.
2. Abra **Pacientes**.
3. En el paciente usado durante el recorrido, seleccione **Vincular cuenta**.
4. Elija la cuenta activa con rol Paciente y confirme.
5. Resultado esperado: aparece **Cuenta vinculada**. No se ofrecen reemplazo ni desvinculación.

### Paciente: portal de solo lectura

1. Cierre sesión e ingrese con la cuenta Paciente vinculada.
2. Abra **Mi información**.
3. Revise las secciones:
   - **Mis datos**.
   - **Mi historia clínica**.
   - **Mis citas**.
   - **Mis consultas y recetas**.
4. Abra el detalle de la receta.
5. Resultado esperado: el paciente ve únicamente información propia y no dispone de acciones para editar datos, citas, consultas o recetas.

## 5. Evidencia de permisos

- Recepcionista: puede gestionar pacientes y citas; no puede registrar enfermedades, consultas o recetas.
- Médico: puede consultar pacientes, su propia agenda, atender citas y emitir recetas; no administra cuentas.
- Paciente: accede a su portal si tiene rol y vinculación válidos; no accede a listados clínicos generales.
- Conductor: no accede al flujo clínico.
- Administrador del sistema: ese rol por sí solo no concede acceso a datos clínicos de una clínica.
- Un usuario con varios roles conserva la unión de sus permisos, pero el rol Paciente sigue requiriendo una vinculación válida.

## 6. Evidencia de aislamiento multitenant

Prepare una segunda clínica ficticia con sus propios usuarios y pacientes.

1. Inicie sesión con un usuario de la clínica A.
2. Intente usar en una URL o petición un identificador conocido de la clínica B.
3. Resultado esperado: la API responde como recurso inexistente o ajeno, normalmente `404 no_encontrado`, sin revelar datos.
4. Ingrese como paciente de la clínica A.
5. Resultado esperado: citas, consultas y recetas corresponden exclusivamente a ese paciente y tenant.

La suite automatizada también compara recursos ajenos e inexistentes y verifica que los intentos rechazados no persisten cambios.

## 7. Verificación técnica final

Backend:

```powershell
Set-Location backend
$env:DEBUG = "True"
.\venv\Scripts\python.exe -m pytest tests\api\sprint2 -v -p no:cacheprovider
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py spectacular --file "$env:TEMP\clinica-sprint2-final.yml" --validate
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

Frontend:

```powershell
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## 8. Limitaciones comprobadas

- El frontend no tiene actualmente una biblioteca de pruebas automatizadas; se verifican tipos, lint y compilación. El recorrido visual debe ejecutarse manualmente.
- La duración técnica de las citas es de 30 minutos y no se persiste como campo configurable.
- Las advertencias de alergias comparan nombres normalizados y son informativas.
- El portal del paciente es de solo lectura.
- Solo `mi-historia` requiere que exista una historia clínica; las demás secciones no incorporan esa dependencia.
- No existe reemplazo ni desvinculación de la cuenta asociada al paciente dentro de S2-12.
