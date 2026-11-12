# Funcionalidades conectadas

Esta entrega completa las pantallas de las APIs de negocio existentes en `/api/v1/`.
No añade endpoints ni modifica el backend.

| API | Pantalla | Acceso y operaciones |
|---|---|---|
| `/auth/login/`, `/auth/refresh/`, `/auth/logout/` | Login y sesión | Inicio, restauración, renovación, reintento y cierre de sesión |
| `/auth/me/` | Mi cuenta | Consultar y actualizar perfil, roles, clínica y suscripción |
| `/auth/cambiar-password/` | Mi cuenta | Cambiar contraseña propia con contraseña actual y confirmación |
| `/clinicas/` | Clínicas | Administrador del sistema: registrar con primer administrador, consultar, editar, desactivar y reactivar |
| `/clinicas/{id}/` | Mi clínica | Administrador de clínica: consultar sus propios datos con suscripción vigente |
| `/planes/` | Planes | Administrador del sistema: crear, consultar, editar, desactivar, reactivar y filtrar por estado |
| `/planes/` | Planes disponibles | Administrador de clínica: consultar catálogo y detalle, incluso en modo restringido |
| `/suscripciones/` | Mi suscripción / Suscripciones | Clínica: contratar, renovar, cambiar plan, cancelar, consultar detalle e historial. Sistema: consulta global |
| `/usuarios/` | Usuarios | Crear, consultar listado, editar correo y contraseña, desactivar, reactivar y buscar |
| `/roles/` | Roles | Crear, consultar, editar, activar/desactivar personalizados, eliminar y buscar. Protección de roles base |
| `/usuario-roles/` | Usuarios → Roles | Consultar asignaciones, asignar roles activos y retirar con confirmación |
| `/personal/` | Personal | Crear, listar, buscar, editar, activar/desactivar y eliminar registros permitidos |
| `/personal/{id}/vincular-usuario/` | Personal → Cuenta | Vincular/desvincular cuentas, excluir cuentas ocupadas, conservar validación del backend |
| `/especialidades/` | Especialidades | Administrador: gestión completa. Médico: listado, búsqueda y consulta |
| `/medicos/` | Médicos | Administrador: registro y gestión con personal, especialidad y colegiatura. Médico: consulta de su propio registro |
| `/horarios/` | Horarios | Administrador: gestión por médico y día. Médico: gestión de sus propios horarios sin enviar un médico ajeno |

## Reglas de la integración

- Los permisos se validan en el servidor; el frontend también protege rutas y oculta acciones no autorizadas.
- El modo restringido permite Mi cuenta, Planes disponibles y Mi suscripción al administrador de clínica.
- Los roles personalizados no crean permisos de API automáticamente.
- Una cuenta de usuario, un registro de personal y un registro médico son entidades diferentes.
- Para habilitar el acceso de un médico: crear usuario con rol Médico, vincularlo a Personal y crear el registro de Médico.
- Desactivar Personal no desactiva automáticamente su cuenta de usuario.
- Los precios mantienen el formato decimal de texto del backend.
- La vigencia de una suscripción del historial se calcula con su estado y fechas; el campo `vigente` actual del backend representa la clínica completa.
- Al editar un horario se conserva su médico. Para trasladarlo a otro médico se elimina y se crea de nuevo. El servicio actual del backend valida solapamientos usando el médico anterior al actualizar; conservar el médico evita una reasignación con validación incorrecta.
- Las listas de referencia recorren todas las páginas. Los formularios muestran errores del servidor y bloquean envíos mientras se guarda.
- El backend no ofrece filtro por usuario en usuario-roles: esa selección se realiza localmente después de recorrer las páginas.

## Alcance pendiente del backend

Pacientes, historias clínicas, enfermedades, alergias, citas, consultas, recetas,
medicamentos, ambulancias, equipamiento, licencias y traslados tienen modelos y
Django Admin, pero no tienen APIs REST registradas. Esta entrega no inventa llamadas
para esos módulos: requieren desarrollar sus APIs antes de integrarlos en React.

`/api/health/`, `/api/docs/`, `/api/schema/` y `/admin/` siguen disponibles en el
backend como herramientas técnicas, fuera de las pantallas de negocio de React.

## Verificación al terminar el código

Se ejecutaron sobre la copia de entrega:

- `npm.cmd run typecheck`: correcto.
- `npm.cmd run build`: correcto.
- `npm.cmd run lint`: correcto.

Vite advierte sobre un paquete JavaScript de más de 500 kB. No impide compilar.
No se hicieron pruebas manuales en navegador ni operaciones reales contra la base
de datos durante esta entrega. Las verificaciones funcionales siguen pendientes.

## Prueba funcional final sugerida

1. Sistema: registrar clínica y administrador, crear plan, editar y reactivar clínica/plan.
2. Clínica nueva sin suscripción: comprobar redirección, consultar planes y contratar con fecha actual.
3. Clínica: crear usuario y rol, asignar/quitar roles, comprobar límite del plan y protección del último administrador.
4. Personal: registrar, vincular cuenta, desvincular y comprobar que una cuenta no se vincule a dos personas.
5. Médico: registrar personal/especialidad/colegiatura; entrar con la cuenta vinculada y consultar su registro.
6. Horarios: crear, editar y eliminar; comprobar rechazo de intervalos superpuestos e inicio posterior al fin.
7. Médico: comprobar que solo vea su registro y sus horarios, y especialidades sin acciones de escritura.
8. Cuenta: cambiar contraseña y volver a iniciar sesión con la nueva.
9. Suscripción: renovar, cambiar plan y cancelar; verificar acceso restringido y restauración tras recargar.
10. Dos clínicas: comprobar que ninguna pueda consultar o modificar datos de la otra.
