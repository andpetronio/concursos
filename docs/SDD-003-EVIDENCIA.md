# SDD-003 — Evidencia de implementación

**Estado:** implementación entregada; aceptación del usuario pendiente. No habilita SDD-004.

## Alcance entregado

Persona reutilizable por DNI normalizado y participaciones por concurso para jurados, veedores de APUNSJ y aspirantes. La ficha separa los tres grupos; las altas y correcciones usan formularios, permisos y componentes compartidos. La base impide duplicar una plaza de jurado o un aspirante dentro del concurso. No se cambian silenciosamente datos de una persona ya registrada.

## Verificación efectuada

| Control | Resultado |
|---|---|
| Revisión independiente inicial | `revisor_django`, `auditor_ui` y `auditor_seguridad`; los hallazgos relevantes se corrigieron y se hizo QA focal. |
| Correcciones verificadas | Versiones optimistas en edición; bloqueo y revalidación del DNI antes de reutilizar Persona; selección inicial obligatoria de representación/calidad del jurado; mensaje claro para plaza duplicada. |
| Django y PostgreSQL aislado | `manage.py check`: 0 problemas; `makemigrations --check --dry-run`: sin cambios; suite completa: **77 pruebas, OK**. `git diff --check`: sin errores. |
| Chrome aislado con datos sintéticos | Revisados 1440, 1280, 768 y 360 px: secciones vacías y pobladas, tres flujos de alta, foco por teclado, selección obligatoria y desplazamiento de tablas angostas; sin desbordamiento horizontal de página. |

**Límite de verificación visual:** la llamada a `showPicker()` devolvió éxito, pero la captura headless no mostró el menú nativo abierto. La inspección visual de ese popup queda pendiente; no se declara comprobada.

## Límites y siguiente paso

No se aplicó la migración a la base persistente. No hubo commit, push ni despliegue. No se implementaron reasignación o desactivación de personas, sustituciones e historial de reemplazos, fotografía histórica definitiva, SDD-004/005 ni integración CoPla. La expresión «DNI duplicado/localidad» de la especificación no define una regla de localidad; no se agregó ninguna. Corresponde la revisión y aceptación expresa del usuario antes de avanzar de fase.

## Ajustes posteriores a pruebas de carga — 23/10/2026

Entrega ajustada por pedido del usuario; sigue pendiente su aceptación. **No habilita SDD-004.**

### Cambios y archivos
- `participantes/models.py`, `forms.py`, `services.py`, `views.py`, `concursos/urls.py` y `templates/participantes/aspirantes_tabla.html`: correo y expediente de inscripción opcionales en Aspirante, consulta y edición independiente de Persona. Nueva versión de inscripción con el mismo servicio de bloqueo/versión de las otras participaciones.
- `core/validators.py`, `core/fields.py`, `core/templates/core/widgets/identificador.html`, `static/js/forms.js` y `templates/layouts/private.html`: DNI de 8 dígitos, normalización textual y ceros preservados; expedientes de central variable 1–9999; widgets, validación y máscaras compartidos. Botón de guion para teclados numéricos, sin dependencias. Teléfono `tel`, correo `email`; todos los DNI/expedientes `text` + `inputmode="numeric"`. No hay fechas editables en los formularios actuales: las fechas de auditoría siguen siendo automáticas.
- `concursos/models.py`, `forms.py`, `services.py`, `views.py`, `templates/concursos/formulario.html` y `static/css/app.css`: funciones opcionales en datos adicionales nativos; contenido conservado y desplegado si existe. Validación de expediente de concurso y advertencia de repetidos sin unicidad nueva. No se copian funciones desde denominación.
- Migraciones `concursos/0002_alter_concurso_funciones` y `participantes/0002_aspirante_email_aspirante_expediente_inscripcion_and_more`: sin borrados ni reescritura de valores; nuevas columnas vacías de inscripción y versión inicial 1. Se conserva tamaño de DNI para datos históricos. Identificadores históricos fuera de formato pueden conservarse en su registro; altas o cambios exigen el formato nuevo.
- Pruebas en `core/tests/test_identificadores.py`, `concursos/tests/test_ajustes.py`, `participantes/tests/test_ajustes.py`, `test_migrations.py` y `test_concurrency.py`; fixtures anteriores actualizadas al formato aprobado y funciones opcionales. Documentación actualizada en PRODUCTO, DECISIONES, DISEÑO, specs 002/003 y README.

### Evidencia ejecutada

| Control | Resultado |
|---|---|
| `docker compose build web` | Imagen local reconstruida con el código final. No se recreó el servicio activo. |
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py test -v 1` | **97 pruebas, OK**, PostgreSQL, 16,316 s. Base exclusiva `test_gestion_concursos`, eliminada por Django al finalizar. |
| Migración con datos anteriores | Prueba con MigrationExecutor desde ambas `0001`: conserva DNI histórico, vínculos, funciones, fechas, historial y responsables; campos nuevos vacíos. |
| Concurrencia PostgreSQL | Continúan pasando las pruebas anteriores; nueva carrera con dos conexiones sobre la inscripción: una escritura y un conflicto, versión final 2. |
| `docker compose run --rm --no-deps web python manage.py check` | Sin problemas (0 silenciados), usando la imagen final sin montaje. |
| `docker compose run --rm --no-deps web python manage.py makemigrations --check --dry-run` | Sin cambios detectados. |
| `docker compose run --rm --no-deps web python manage.py migrate --plan` | Inspección de migraciones pendientes, sin aplicación a la base persistente. |
| `docker compose run --rm --no-deps web python -m pip check` | Dependencias verificadas en la imagen final. |
| `git diff --check` | Sin errores; Git informa conversión futura LF/CRLF en algunos archivos de texto. |
| Chrome local aislado | 30 capturas, viewports internos comprobados de **360/768/1280 px**, **453 comprobaciones DOM, 0 fallos**. Máscaras al escribir/borrar/pegar/editar, cursor, ceros, email/expediente inválidos, DNI histórico, guion sin teclado alfanumérico, etiquetas, desbordes, foco con Tab y desplegable con Enter. |

QA visual generada con `.venv/Scripts/python.exe artifacts/ajustes-sdd003/render_forms.py` y `node artifacts/ajustes-sdd003/capture_viewports.mjs`. HTML real obtenido de vistas Django mediante cliente de pruebas con SQLite en memoria y solo datos sintéticos; recursos compartidos reales, JS de sesión deshabilitado solo en esos archivos de QA. Chrome headless usa perfil descartable del proyecto. Se detectó y descartó el primer intento de captura de 360 px que Chrome CLI recortaba por el mínimo de ventana: las capturas definitivas fijan y comprueban el viewport real. El control CUA no tenía navegadores disponibles.

Capturas, scripts y `summary.json` quedan en `artifacts/ajustes-sdd003/`, ignorados por Git y excluidos de la imagen. El principal inspeccionó visualmente alta de aspirante a 360, errores a 768, edición de concurso a 1280 y edición de persona a 360. Esto verifica renderizado y DOM; los flujos HTTP de guardado los comprueba la suite Django. No se verificó un teclado virtual físico ni se repitió la inspección del popup nativo de selects.

### Revisiones focalizadas
- `revisor_django`: cerró el hallazgo de comparación de DNI sin normalizar en invocación directa del servicio de edición; corrección comprobada y cubierta por prueba. Sin observaciones pendientes.
- `auditor_ui`: inspeccionó el diff y capturas reales a 360/768/1280; se resolvió la entrada de guiones con teclado numérico mediante el widget compartido. Sin correcciones pendientes. Tab/Enter reales se comprobaron después mediante eventos de teclado en el renderizador de Chrome.

### Estado operativo
No se aplicaron estas migraciones a la base persistente ni se reinició/recreó el servicio activo. La imagen está preparada y las dos migraciones fueron probadas sobre bases de prueba. No hubo commit, push, despliegue ni cambios en CoPla. No se inicia SDD-004. Corresponde revisar y aceptar los ajustes antes de avanzar.

## Ajuste puntual de jurados — Unidad en lugar de Cargo (23/10/2026)

Unidad es obligatoria en alta y edición, como destino organizativo del integrante, independiente de la dependencia del cargo concursado. Se almacena en Jurado por participación y comparte definición entre ambos formularios. Cargo deja de ser entrada y de exigirse, pero se conserva en la base y en la ficha como «Cargo registrado anteriormente». Título, DNI, contacto, representación/calidad, permisos, plaza única, responsables y edición con versión/bloqueo mantienen sus reglas.

Archivos del ajuste: `participantes/models.py`, `forms.py`, `migrations/0003_jurado_unidad_alter_jurado_cargo.py`, `tests/test_participantes.py`, `tests/test_migrations.py`, `templates/participantes/jurados_tabla.html`, spec 003, PRODUCTO, DECISIONES, README y esta evidencia. Las vistas y servicios genéricos existentes procesan los campos validados de los formularios; no necesitaron otra implementación. Sin CSS/JS nuevo ni cambios en aspirantes o veedores.

Antes de migrar se consultaron solo cantidades en la base local: **6 jurados, los 6 con cargo registrado**, sin mostrar datos personales. La migración agrega Unidad vacía mediante un default temporal (`preserve_default=False`), sin derivarla de Cargo o del concurso. La ficha muestra «Pendiente de completar» para esos jurados; al editar deben informar la unidad. No se ejecutó la migración sobre la base persistente.

| Verificación | Resultado |
|---|---|
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py test participantes -v 1` | 31 pruebas, OK (ejecución inicial, antes de incorporar la prueba específica de migración de Unidad). |
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py test -v 1` | **113 pruebas, OK**, PostgreSQL, 18,046 s. Incluye permisos y controles de concurrencia previos; Django eliminó únicamente su base de pruebas al terminar. |
| Casos nuevos/actualizados | Unidad obligatoria en alta/edición, vacíos/espacios/longitud, alta sin cargo, edición que ignora un Cargo inyectado y conserva el anterior, todos los demás datos del jurado, unidad independiente entre concursos y consulta de pendientes/históricos. |
| Migración con registros anteriores | MigrationExecutor desde `participantes.0002`: compara todos los valores del Jurado antes/después, con unidad nueva vacía; conserva cargo, identidad, vínculo, contacto, plaza, versión, responsables y fechas. Reversión probada con cargo original intacto. |
| `manage.py check` | Sin problemas (0 silenciados), ejecutado en Compose con el código montado. |
| `manage.py makemigrations --check --dry-run` | Sin cambios detectados, ejecutado en Compose con el código montado. |
| `manage.py migrate --plan` | Pendiente únicamente `participantes.0003_jurado_unidad_alter_jurado_cargo` (agregar Unidad y volver opcional Cargo), sin aplicación. |
| Chrome aislado | **15 capturas, 183 comprobaciones DOM, 0 fallos**, viewports reales de 360/768/1280 px; alta, edición, errores, ficha con unidad e información histórica pendiente, etiquetas, requerimiento HTML, tipos preservados, tablas contenidas y Tab real. |
| `docker compose build web` | Imagen local reconstruida con el ajuste, sin recrear el servicio activo. |
| `git diff --check` | Sin errores; avisos de conversión futura LF/CRLF en algunos archivos de texto. |

QA reproducible local: `.venv/Scripts/python.exe artifacts/jurados-unidad/render_forms.py` y `node artifacts/jurados-unidad/capture_viewports.mjs`. HTML real de vistas Django con SQLite en memoria y datos sintéticos; assets compartidos reales y perfil descartable de Chrome. JS de sesión deshabilitado solo en esos archivos de QA. Capturas, scripts y `summary.json` en `artifacts/jurados-unidad/`, ignorados por Git y excluidos de la imagen. Los guardados HTTP los verifica Django; no se inspeccionó un teclado virtual físico.

Revisión focalizada de `revisor_django` y `auditor_ui` finalizada sin hallazgos. Auditor UI inspeccionó cinco capturas de formularios y fichas a los tres anchos; principal inspeccionó alta a 360, error a 768 y edición a 1280. Componentes compartidos e identidad blanco/naranja conservados.

No se modificó la base persistente ni se recreó el servicio activo. No hubo commit, push o despliegue. SDD-004 no iniciada; corresponde revisión del usuario de este ajuste.
