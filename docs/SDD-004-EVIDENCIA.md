# SDD-004 — Evidencia de implementación

**Fecha:** 23/10/2026. **Estado:** implementada y verificada; pendiente de aceptación funcional del usuario. SDD-001/002/003 y sus ajustes fueron aceptados expresamente al autorizar esta fase. No habilita SDD-005.

## Resultado y archivos

- Nueva app `expedientes`: catálogo central de 19 requisitos en cinco secciones; modelos de controles, seguimiento de etapa y sus dos bitácoras; formularios, normalizador de fojas, servicios transaccionales, vistas y presentación. Unicidad concurso/requisito y restricciones de catálogo/etapa en PostgreSQL. Sin admin, eliminación ni endpoints de edición de bitácoras.
- `expedientes/migrations/0001_initial.py` inicializa los 19 controles anteriores sin atribuir verificaciones. `0002_etapa_documental.py` crea seguimiento y etapa inicial Preparación, sin inferir el avance administrativo ni cambiar datos existentes. El alta nueva inicializa ambos explícitamente dentro de su transacción.
- `concursos/services.py`, `views.py`, `urls.py`, `config/settings.py`: registro del módulo, alta explícita, contexto en ficha, rutas anidadas e integración de sugerencia con el formulario de estado existente. Permisos, versiones y concurrencia de participantes/datos generales permanecen vigentes.
- `templates/expedientes/`, `templates/concursos/detalle.html`, `templates/components/checkbox_field.html`, `static/css/app.css`: resumen, etapa manual, filas editables o consulta, fojas solo donde corresponden, correcciones e historial de etapas; componentes y tokens compartidos. Sin JS nuevo de aplicación ni dependencias añadidas.
- `expedientes/tests/test_documental.py`, `test_concurrency.py`, `test_migrations.py`: 27 pruebas nuevas; 140 en la suite completa.
- Documentación actualizada: spec 004, PRODUCTO, DECISIONES, ROADMAP-SDD, DISEÑO y README. No se reescribe la evidencia histórica de fases previas; la aceptación posterior consta en el roadmap y decisiones.

## Decisiones funcionales verificadas

- El usuario eligió expresamente **etapa documental activa manual**. Sus requisitos y los anteriores son exigibles; pendientes posteriores se muestran neutrales. Avanzar/retroceder etapa no borra controles y conserva responsable/fecha/antes/después/versiones. Estado administrativo independiente.
- Cinco controles previos, cuatro fojas válidas, seis plazas de jurado identificadas según datos obligatorios existentes y datos generales válidos habilitan el **proyecto** de convocatoria. Servicio informa faltantes por documentos, jurados y datos. No exige veedores ni aspirantes, ni contacto opcional, ni interpreta esta habilitación como acto emitido.
- Se admite carga parcial de check sin foja; sigue incompleto. Referencias inválidas se rechazan conservando la entrada. `5`, `5/8`, `12/15`, `105/109` válidos; cero, negativos, decimales, letras y rango inverso rechazados; espacios normalizados. Los requisitos sin foja no tienen ese campo.
- Registro fuera de secuencia permitido, con advertencias visibles. La aprobación sin comunicación del dictamen no bloquea el guardado. Tres temas conserva un único control.
- Dictamen completo sugiere Con dictamen desde estados anteriores; no altera el estado ni historial administrativo. Solo un usuario con permiso de cambio de estado puede confirmar por el flujo existente. No se propone Finalizado ni se infiere Convocado de publicación.
- `consultar_documentacion` devuelve verificados, completos, fojas, pendientes globales/exigibles/futuros, advertencias, sugerencia y habilitación. `habilitacion_convocatoria` puede usarse sin UI. Las consultas no inicializan registros ni generan documentos.

## Comandos y resultados

Comandos ejecutados desde la raíz. Docker usa PostgreSQL del entorno local; Django crea y destruye su base exclusiva `test_gestion_concursos`. No se aplicaron migraciones a la base persistente.

| Comando | Resultado |
|---|---|
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py test -v 1` | **140 pruebas, OK, 23,941 s**, PostgreSQL; primera ejecución integral de SDD-004. |
| `docker compose build web` | Imagen local reconstruida; sin `up`, recreación del servicio, push ni despliegue. |
| `docker compose run --rm --no-deps web python manage.py test -v 1` | **140 pruebas, OK, 22,914 s**, sobre la imagen construida después de corregir los dos hallazgos de UI. Base de prueba eliminada al finalizar. |
| `docker compose run --rm --no-deps web python manage.py check` | `System check identified no issues (0 silenced).` |
| `docker compose run --rm --no-deps web python manage.py makemigrations --check --dry-run` | `No changes detected`. |
| `docker compose run --rm --no-deps web python -m pip check` | `No broken requirements found.` |
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py migrate --plan` | Solo pendientes `expedientes.0001_initial` y `expedientes.0002_etapa_documental`; consulta sin aplicar. |
| `git diff --check` | Exit 0, sin errores de whitespace; avisos de conversión LF/CRLF de Git en archivos del workspace. |

Cobertura nueva: 19 requisitos de alta/existentes, restricciones en base, fojas, cargas parciales, no-foja, preparación completa/incompleta y jurados faltantes/históricos incompletos, servicios, secuencia, sugerencia/confirmación, permisos de consulta/documental/estado, IDOR, no eliminación, CSRF, expiración exacta a 1800 s y GET automático sin renovar, no-op, rollback ante falla de bitácora y preservación de entrada ante conflictos.

Concurrencia real PostgreSQL mediante conexiones/hilos independientes: dos ediciones del mismo control guardan una y rechazan la versión vieja; controles distintos conservan ambos cambios; selección de etapa concurrente conserva una edición y un evento atómico. La migración compara snapshots completos de Concurso, Persona, Aspirante e historial administrativo antes/después y comprueba 19 controles sin marcas ficticias y etapa inicial.

## Revisión visual real

Chrome headless con perfil local aislado, sin usar sesiones del usuario. Ocho pantallas Django sintéticas: vacío, preparación completa, error de foja, documentación fuera de secuencia/sugerencia, solo consulta, conflicto de etapa, historial de control e historial de etapa. Anchos reales **360, 768, 1280 y 1440 px**.

- **32 combinaciones, 392 comprobaciones sin fallos**: catálogo/grupos, fojas/observaciones, etiquetas, IDs únicos, checkbox nativo blanco/naranja, versiones, estados, errores conservados, readonly, ausencia de desbordes, fondo y navegación Tab/Espacio reales. Capturas de resumen y detalles de inscripciones, oposición y finalización; inspección visual de variantes críticas por agente principal y auditor UI.
- Selector de etapa abierto con **Alt+Flecha abajo real**, `:open` verdadero y captura del menú nativo con cinco opciones, foco naranja, flecha y padding. Verificación focal: **17 comprobaciones sin fallos**.
- Errores de check y etapa navegados mediante fragmento en los cuatro anchos: **8 combinaciones, 144 comprobaciones sin fallos**, incluida ubicación visible del formulario bajo el encabezado fijo.
- Artefactos locales ignorados: `artifacts/sdd004/render_forms.py`, `test_documental.js`, `capture_viewports.mjs`, `check_select.mjs`, `check_anchors.mjs`, `summary.json`, `select-summary.json`, `anchors-summary.json` y PNG. Ejecución: `.venv/Scripts/python.exe artifacts/sdd004/render_forms.py` y `node artifacts/sdd004/<script>.mjs`.

**Límite:** el navegador abrió HTML de respuestas Django reales con datos sintéticos y estáticos locales; `session.js` se desactivó únicamente en el fixture de renderizado. No se declara probado un envío HTTP de extremo a extremo desde ese navegador. Los POST reales, permisos, CSRF, sesión, persistencia y migraciones se comprobaron por Django Client y servicios contra PostgreSQL. No se usaron datos personales reales.

## Revisiones independientes focalizadas

| Revisor | Resultado y resolución |
|---|---|
| `revisor_django` (`revision_django_ajustes`) | Sin hallazgos materiales; revisó persistencia/migraciones, validación, inicialización, locking/versiones, bitácoras, preparación y servicios. Solo lectura; no repitió suite ni auditoría de fases anteriores. |
| `auditor_ui` (`revision_ui_ajustes`) | Dos hallazgos corregidos: nombre accesible del checkbox debe contener etiqueta visible «Verificado» y acciones POST deben incluir ancla para localizar errores. Agregadas pruebas de respuesta y navegación real. Revisó nueve capturas, luego selector y anclas; cierre sin hallazgos ni comprobaciones pendientes. |
| `auditor_seguridad` (`revision_seguridad_sdd004`) | Sin vulnerabilidades demostrables: POST/CSRF, permisos en vistas/servicios, anidado por concurso, historiales de consulta, concurrencia/auditoría atómica y permiso independiente de estado. Leyó pruebas de sesión/expiración; sin repetir PostgreSQL compartido ni modificar autenticación. |

## Pendientes y operación posterior

1. **Aceptación funcional del usuario.** La entrega se detiene aquí. No se inicia SDD-005.
2. Aplicar las dos migraciones pendientes antes de servir la nueva imagen, conservando `.env` y el volumen; los comandos de actualización local están en README. La base persistente y el servicio activo no se modificaron en esta entrega.
3. Asignar explícitamente el permiso documental a las cuentas que deban operar; no se asignaron roles/permisos a usuarios existentes.

Sin commit, push, despliegue, borrado de datos persistentes, generación Word/PDF, integración CoPla, nuevos estados administrativos o circuitos extraordinarios.

## Corrección funcional — Convocatoria, 23/10/2026

La validación funcional amplía el catálogo de **19 a 21 requisitos**, sin cambiar los cinco bloques. Convocatoria presenta publicación (6), oficio a APUNSJ solicitando veedor (7) y notas de notificación a jurados (8). Los dos nuevos son obligatorios conforme a la etapa activa, sin foja y de carga en cualquier orden; las notificaciones tienen un único check para los seis titulares y suplentes. La ausencia de veedor designado no bloquea el avance y la futura generación en SDD-005 no marca controles automáticamente.

Archivos de esta corrección: `expedientes/catalogo.py` (dos definiciones y ayudas), `services.py` (secuencia desde identificador Acta de inscriptos, sin posiciones fijas), `templates/expedientes/control_fila.html` (ayuda compartida también en consulta), migraciones nuevas `0003_controles_convocatoria` y `0004_incorporar_controles_convocatoria`, pruebas documentales/migraciones, spec 004, PRODUCTO, DECISIONES y README. No se agregan CSS, scripts de aplicación, permisos ni automatismos. Los cinco controles previos de habilitación permanecen iguales.

La migración de esquema amplía choices y restricción de identificador; la siguiente agrega solo los dos controles faltantes mediante `get_or_create`. Separar esquema y datos permite avance/reversión en PostgreSQL sin mezclar cambios DDL con eventos de integridad referencial pendientes. Las migraciones anteriores no se modifican. No se actualizan ni recrean los 19 controles previos, etapa o bitácoras. Reejecutar la carga no pisa siquiera controles nuevos utilizados. Una reversión solo elimina semillas nuevas intactas; si tienen datos o historial, se detiene conservando la información.

| Verificación ejecutada para la corrección | Resultado |
|---|---|
| `docker compose run --rm --no-deps --volume C:/Users/Usuario/Desktop/SiCon:/app web python manage.py test -v 1` | **144 pruebas, OK, 27,315 s**, suite completa PostgreSQL; base exclusiva de pruebas eliminada al finalizar. |
| Mismo comando de Compose con `python manage.py check` | 0 problemas. |
| Mismo comando con `python manage.py makemigrations --check --dry-run` | `No changes detected`. |
| Mismo comando con `python manage.py migrate --plan` | Pendientes solamente `expedientes.0003_controles_convocatoria` y `0004_incorporar_controles_convocatoria`; consulta sin aplicar. |
| `docker compose build web` y `docker compose run --rm --no-deps web python manage.py check` | Imagen local de la corrección reconstruida; check sobre la imagen sin montaje: 0 problemas. Sin recrear el servicio activo. |
| `git diff --check` | Exit 0, sin errores; avisos LF/CRLF de archivos del workspace. |

Regresiones verificadas: 21 controles nuevos/existentes, orden de las cinco secciones y números 1–21, convocatoria 6/7/8, un único check de notificaciones, ausencia/rechazo de fojas donde no corresponden, exigibilidad desde Convocatoria y etapas siguientes, futuro neutral en Preparación, registro en cualquier orden sin advertencias falsas, habilitación previa sin exigir los controles nuevos ni un veedor. Migración con snapshots exactos de los 19 controles anteriores y sus bitácoras/seguimiento; preservación de PK, checks, fojas, observaciones, responsables, fechas y versiones; idempotencia y reversión conservadora. Los tests previos de concurrencia, sesión y permisos siguen aprobados.

Revisión visual Chrome aislado: **12 combinaciones de tres escenarios (vacío, Convocatoria activa con una notificación verificada, consulta) y cuatro anchos (360/768/1280/1440), 216 comprobaciones sin fallos**, con capturas de los nuevos controles y sus ayudas. Incluye teclado Tab/Espacio, ausencia de desbordes, etiquetas y número de campos según permisos. Artefactos sintéticos ignorados en `artifacts/sdd004-convocatoria/`; mismo límite del renderizador descrito arriba: HTML de respuestas Django real con estáticos locales, sesión JS desactivada solo en fixture; persistencia/POST/migraciones probados contra PostgreSQL mediante Django, no envío HTTP completo desde Chrome.

Revisiones independientes **focalizadas, sin repetir auditorías completas**: `revision_django_ajustes` confirmó migraciones, preservación, idempotencia, secuencia y preparación sin hallazgos; `revision_ui_ajustes` confirmó orden, ayudas/check general visibles también en consulta y capturas sin hallazgos. Ambos de solo lectura, sin ejecutar otra suite PostgreSQL compartida.

Corrección terminada, pendiente de aceptación funcional. Las dos migraciones nuevas no se aplicaron a la base persistente ni se recreó el servicio. Sin SDD-005, commit, push, despliegue ni otras funcionalidades.
