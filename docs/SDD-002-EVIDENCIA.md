# Evidencia SDD-002 — Concursos, ficha y estados

Fecha: 22/10/2026. Alcance autorizado: exclusivamente `docs/specs/002-concursos.md`. Se implementó el registro, consulta, edición y cambio manual auditado de estados/situaciones. La validación visual real sigue pendiente porque no hubo navegador disponible; no se declara aprobada por los tests de backend.

## Criterios confirmados y decisiones

El usuario confirmó expresamente:

- Permitir expedientes repetidos hasta definir el ámbito de unicidad.
- Texto libre para modalidad, agrupamiento, categoría y tramo, con los datos mínimos obligatorios. Campos complementarios fuera de esta fase.
- Permisos Django separados para consultar, crear, editar y cambiar estado/situación. Sin eliminación de concursos.

Se actualizaron la especificación y `docs/DECISIONES.md` con esas respuestas. Los catálogos y el ámbito de unicidad futuros siguen pendientes; no se inventaron reglas normativas ni validaciones de categoría, modalidad o expediente.

Decisiones técnicas:

- `Concurso` conserva sus propios datos de cargo/estructura como texto, sin enlaces con estructuras externas que puedan modificarlo automáticamente. Estado inicial **Preparación**, situación inicial **Normal**.
- `CambioEstado` conserva también el alta inicial y cada cambio efectivo, con usuario, fecha, valores anteriores/nuevos y justificación opcional. Estado y situación son independientes y se eligen manualmente, sin transiciones automáticas ni bloqueos documentales.
- Servicios acotados para creación auditada, actualización de datos y cambio de estado. Locks de fila, transacciones y versión esperada evitan sobrescrituras y eventos duplicados entre operadores. Si falla la auditoría, se revierte la operación completa.
- Las vistas usan ModelForms/Forms, ORM y mixins de autenticación/permisos nativos. Los datos aceptados están delimitados; estado y autor no se toman del formulario de datos generales.
- Permisos `view_concurso`, `add_concurso`, `change_concurso`, `cambiar_estado_concurso`. Toda escritura requiere además consulta. No se concedieron permisos automáticamente, no se crearon roles nuevos y no se registraron los modelos en el admin para evitar una vía de edición ajena al historial.
- Listado e historial paginados de a 20; búsqueda por expediente/cargo/código y filtro de estado combinables. Consultas relacionadas del historial y responsables con `select_related`.
- Reutilización del layout privado, botón, campo, mensajes, cabecera, tarjetas y tokens existentes. Se incorporaron componentes compartidos de tabla, estado, paginación, resumen de errores y vacío. Sin CSS por pantalla, colores nuevos ni dependencias adicionales.
- La asociación ARIA de campos y errores usa el comportamiento nativo de Django 5.2, con IDs coincidentes y únicos en el componente compartido. Se retiró la implementación manual de ARIA del login.
- La política de sesión mantiene los 1800 segundos, el reloj en servidor y las mismas señales. Solo se incluyeron las rutas `/concursos/` en la navegación intencional ya reconocida. Los nuevos POST y requests automáticos no prolongan el reloj por sí solos.
- Como en SDD-001 y `docs/SEGURIDAD.md`, la vigencia se comprueba al admitir cada request, después de tomar el lock del reloj y antes de ejecutar la vista. No se cancela por temporizador una transacción ya admitida; esta fase no incluye tareas largas. El endpoint de renovación conserva su comprobación adicional antes de renovar.

## Archivos nuevos

- `concursos/__init__.py`, `apps.py`, `choices.py`, `models.py`, `forms.py`, `services.py`, `views.py`, `urls.py`.
- `concursos/migrations/__init__.py`, `0001_initial.py`.
- `concursos/tests/__init__.py`, `test_concursos.py`, `test_concurrency.py`.
- `templates/concursos/lista.html`, `lista_tabla.html`, `formulario.html`, `detalle.html`, `estado.html`, `historial_tabla.html`.
- `templates/components/empty_state.html`, `status.html`, `table.html`, `pagination.html`, `form_errors.html`.
- Este archivo de evidencia.

## Archivos existentes modificados

- `config/settings.py`, `config/urls.py`: app y rutas de concursos.
- `core/middleware.py`: misma validación de sesión, ampliación acotada de rutas de navegación intencional.
- `core/forms.py`, `core/tests/test_auth.py`: ARIA nativa y regresión de ID único.
- `templates/components/button.html`, `field.html`, `navigation.html`: enlaces, controles reutilizados y navegación activa según permisos.
- `templates/core/dashboard.html`, `forbidden.html`: acceso real a concursos y mensaje reutilizable de acceso restringido.
- `static/css/app.css`: controles, tablas con scroll interno, filtros, ficha, estados y responsive, utilizando los tokens existentes.
- `README.md`, `docs/DECISIONES.md`, `docs/ROADMAP-SDD.md`, `docs/specs/002-concursos.md`.

`requirements.txt`, Dockerfile, Compose, tokens, JS de sesión, límites y configuración de cookies no se modificaron en SDD-002. Las skills utilizadas estuvieron disponibles y se leyeron: `sdd-entrega`, `django-calidad`, `ui-consistente` y, para la integración/verificación de sesión, `sesion-segura`.

## Comandos y resultados reales

Entorno principal: Docker Desktop Linux en Windows/PowerShell, Python 3.13.17 y PostgreSQL 17.11 existentes. Se reutilizó el `.env` local ignorado y se conservó el volumen persistente.

| Comando / comprobación | Resultado |
|---|---|
| `docker compose config --quiet` | Exit 0 |
| `docker compose up -d --build web` | Imagen reconstruida, web Up y db healthy |
| `docker compose exec -T web python manage.py migrate --noinput` | `Applying concursos.0001_initial... OK` |
| `docker compose exec -T web python manage.py check` | `System check identified no issues (0 silenced).` |
| `docker compose exec -T web python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `docker compose exec -T web python manage.py migrate --check` | Exit 0, sin pendientes |
| `docker compose exec -T web python manage.py test -v 1`, después de las correcciones | **`Ran 58 tests in 10.002s` / `OK`**, sin skips |
| `docker compose exec -T web python -m pip check` | `No broken requirements found.` |
| Diagnóstico local: `.venv/Scripts/python.exe manage.py test --settings=config.test_settings -v 1` | 58 tests, `OK (skipped=2)`, 0.943 s; las dos pruebas de locks PostgreSQL se omiten en SQLite |
| Node del runtime: `node --check static/js/session.js` | Exit 0; solo sintaxis, sin ejecución en navegador |
| HTTP real con urllib dentro de web | `/health/`, `/ingresar/`, CSS compartido, tokens y JS: 200. `/concursos/` anónimo terminó en `/ingresar/` mediante redirección |
| `docker compose ps` | db healthy, web Up, solo `127.0.0.1:8000` publicado |
| `git check-ignore .env .venv` | Ambos ignorados; `git ls-files -- .env` no devolvió archivos |

Las 58 pruebas incluyen las 25 de fundaciones y 33 nuevas de concursos. La primera ejecución local de los tests nuevos detectó cuatro fallos del helper de pruebas: intentaba cambiar de usuario mediante login sin cerrar una sesión ya autenticada. Se corrigió el helper para cerrar sesión antes de cada login; no se debilitó el login ni la comprobación de permisos. La primera suite completa en PostgreSQL pasó 58/58 en 9.395 s; la suite final indicada arriba corresponde a la versión posterior a las correcciones de revisión.

Cobertura de comportamiento:

- Alta, auditoría inicial, duplicados permitidos, datos requeridos, longitudes y conservación de entrada inválida.
- Edición de datos sin cambios ocultos de estado, independencia de las fotografías de cargo/estructura y registro de última modificación.
- Todos los estados principales, cambio de situación independiente, retorno manual a Preparación, justificación opcional, rechazo de valores inválidos y de envíos sin diferencias.
- Conflictos de formularios desactualizados, reenvío de estado y versión faltante. Rollback de alta/estado cuando falla el historial.
- Búsqueda por expediente, denominación, funciones y código, filtros combinados, filtros inválidos, estados vacíos y paginación que conserva filtros.
- Detalle e historial con escape de texto, autor y fecha; secciones futuras sin enlaces.
- Anónimos y usuarios sin permisos; lector sin escritura; permisos separados de edición y estados; CSRF en las tres escrituras.
- Sesión vencida a los 1800 s bloquea alta, edición y cambio de estado sin modificar registros. Polling y precargas no renuevan; navegación intencional anterior al límite sí.
- Conexiones PostgreSQL concurrentes: dos operadores con la misma versión producen un guardado y un conflicto, con un único evento nuevo coherente con el estado final.
- Sin rutas de eliminación, métodos DELETE rechazados y referencias de auditoría protegidas ante eliminación de concurso/usuario.

El runner creó la base de pruebas desde cero, aplicó todas las migraciones y eliminó exclusivamente esa base de pruebas. No se borraron datos persistentes ni se cargaron concursos/usuarios demo en la base operativa. Las verificaciones Docker se ejecutaron con autorización de la herramienta tras el acceso denegado inicial del sandbox al motor.

## Revisiones independientes de solo lectura

| Revisor | Resultado y evidencia |
|---|---|
| `revisor_django` | Sin defectos demostrables en modelos, migraciones, validación, servicios, concurrencia y permisos. Ejecutó independientemente 7 pruebas en SQLite exclusivamente en memoria: **7/7**, `check` sin errores. No utilizó la base PostgreSQL compartida ni modificó archivos |
| `auditor_ui` | Detectó ID de error duplicado: el wrapper del componente repetía el ID que Django asigna a ErrorList. Se quitó el ID del wrapper, conservando el nativo y su referencia ARIA; se agregaron aserciones de unicidad en login y concurso. También se hizo neutral el resumen compartido para filtros GET. Confirmó ambas correcciones mediante render en memoria, **exit 0 / PASS**, sin escrituras. Sin otros defectos importantes demostrables |
| `auditor_seguridad` | Sin defectos demostrables pendientes en permisos, CSRF, autor de servidor, lista de campos permitidos, historial atómico y sesión. Verificó la conservación de la semántica de admisión de requests de SDD-001. No utilizó la base PostgreSQL compartida ni modificó archivos |

La salida final de 58 tests en PostgreSQL se comunicó a los tres revisores. Su lectura/render/pruebas en memoria no se presentan como revisión visual ni como sustituto de la concurrencia real, que verificó el agente principal en el contenedor.

## QA, límites y uso

- [x] Alcance exclusivo SDD-002; sin participantes, checklist, DOCX ni CoPla.
- [x] Criterios funcionales pendientes confirmados por el usuario y documentados.
- [x] ORM, Forms, permisos y CSRF nativos; sin dependencias nuevas.
- [x] Layout/componentes y tokens blanco/naranja reutilizados; errores y vacíos revisados por render y pruebas.
- [x] Estado y situación independientes, manuales y auditados; sin eliminación expuesta.
- [x] Migraciones/checks/suite PostgreSQL completos, con pruebas de límites y concurrencia.
- [x] Revisiones independientes realizadas y hallazgo importante corregido/verificado.
- [x] README actualizado con arranque, permisos, uso y pruebas; entorno y datos existentes conservados.
- [ ] Verificación visual real a **360/768/1280 px**, recorrido por teclado y ejecución JS en navegador.

**Limitación exacta de UI:** la consulta actual `cua.getState()` devolvió **`apps: []`, `browsers: []`**. No se dispuso de navegador conectado. No hubo screenshots ni pruebas visuales reales. La revisión de CSS, renders, IDs, HTTP y tests no sustituye esa comprobación. Tampoco se ejecutaron comandos desde macOS; las instrucciones de ambos shells están documentadas.

Al inicio `git status` devolvió «not a git repository». Durante la tarea apareció un repositorio con archivos ya preparados en el índice. El agente no ejecutó `git init`, `git add`, commits ni cambios del índice. `git diff --check` sobre los cambios de trabajo no señaló errores de espacios; la revisión del índice existente señaló una línea vacía final en `core/admin.py:21`, archivo no modificado en esta fase. Git también emitió avisos de normalización LF/CRLF. No se alteraron esos archivos preparados para ocultar el diagnóstico.

Los servicios quedan iniciados. Para usar concursos, ingresar en <http://127.0.0.1:8000/concursos/> con un superusuario o conceder al usuario los permisos descritos en README desde el admin nativo. Las cuentas existentes no ganan permisos automáticamente. Para repetir la suite: `docker compose exec web python manage.py test -v 2`.

SDD-002 entregada con el límite visual declarado. No se avanza a SDD-003 ni se hicieron commits, pushes o despliegues.
