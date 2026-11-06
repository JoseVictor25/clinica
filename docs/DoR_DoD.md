# Definition of Ready y Definition of Done

**SaaS Multitenant de Clínicas · Sprint 0**

Estas definiciones aplican a todas las historias de usuario de los Sprints 1 y 2.
Una historia no entra en un sprint si no cumple el DoR, y no se considera terminada
si no cumple el DoD.

## Definition of Ready (DoR)

Una historia está lista para ser tomada por el equipo cuando:

1. **Formato de historia completo:** tiene título, descripción, rol, necesidad y
   beneficio, con criterios de aceptación verificables.
2. **Criterios de aceptación claros:** describen comportamiento observable, incluyen
   casos de éxito, error y permisos, y no dejan decisiones funcionales abiertas.
3. **Dependencias identificadas:** se conocen las historias, tablas y endpoints
   previos necesarios; si depende de otra historia, esta está terminada o planificada
   en el mismo sprint.
4. **Diseño técnico acordado:** se identifican modelos, serializers, endpoints,
   permisos y el filtro multitenant que aplica. Si requiere un cambio de esquema,
   existe una tarea de migración asociada.
5. **Prototipo o referencia visual disponible:** para historias con interfaz, existe
   wireframe o descripción de pantalla aprobada (Sprint 1 en adelante).
6. **Datos de prueba definidos:** se sabe con qué clínica, usuarios y registros se
   validará la historia, incluyendo un caso de aislamiento entre dos clínicas.
7. **Estimada y priorizada:** el equipo la estimó, cabe en un sprint y está ordenada
   en el tablero Scrum.
8. **Sin bloqueos externos:** no depende de accesos, credenciales, servicios o
   decisiones pendientes de terceros.

## Definition of Done (DoD)

Una historia se considera terminada cuando:

1. **Código implementado y revisado:** cumple los criterios de aceptación, sigue las
   convenciones del proyecto y recibió al menos una revisión aprobatoria.
2. **Pruebas automatizadas pasando:** la suite completa (`pytest`) está en verde y la
   historia agrega pruebas de los casos felices, errores y permisos.
3. **Aislamiento multitenant verificado:** se demuestra con pruebas que un usuario de
   la clínica A no puede listar, leer, modificar ni eliminar datos de la clínica B.
4. **Migraciones aplicables:** si hubo cambios de modelo, `makemigrations` no detecta
   cambios pendientes y `migrate` se aplica sin errores sobre PostgreSQL.
5. **Endpoint documentado:** si expone API, aparece en Swagger/OpenAPI
   (`/api/docs/`) con parámetros, respuestas y permisos descritos.
6. **Pull Request aprobado y fusionado:** el cambio está integrado en `develop` mediante
   PR revisado; no quedan ramas de trabajo abiertas para la historia.
7. **Sin secretos ni datos sensibles:** no se agregaron credenciales al código, los
   logs no exponen contraseñas ni tokens y los permisos se validan en el backend.
8. **Demo aceptada:** el Product Owner verificó la historia en el entorno de desarrollo
   con datos de prueba y registró la aceptación en el tablero.
