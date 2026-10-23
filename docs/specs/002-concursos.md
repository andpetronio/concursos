# SDD-002 — Concursos, ficha y estados

**Estado:** AUTORIZADA por pedido del usuario del 22/10/2026. Alcance exclusivo SDD-002.

## Objetivo
Alta, listado, edición y ficha de concursos; estado principal y situación administrativa adicional con cambios auditados.

## Datos mínimos
Expediente, tipo/modalidad, denominación/funciones del cargo, agrupamiento, categoría, tramo, código presupuestario, unidad y dependencia/cadena jerárquica. Los datos generales **no requieren foja**. Mantener fotografía histórica de cargo y estructura.

## Estados
Principales: Preparación (inicial), Convocado, En curso, Con dictamen, Finalizado. Situaciones adicionales: Normal, Impugnado, Suspendido. Cambio manual autorizado con historial usuario-fecha-anterior-nuevo-justificación opcional. El estado no depende mecánicamente del porcentaje de checks. En esta fase las sugerencias automáticas pueden quedar sin implementar hasta existir eventos documentales.

## UI
Listado con filtros por estado y búsqueda por expediente/cargo/código; creación, edición, detalle y estados vacíos. Ficha con navegación futura claramente rotulada, sin enlaces rotos. Mismo diseño de SDD-001.

## Criterios de aceptación
CRUD autenticado y protegido; validación de datos; migraciones; historial de estado comprobable; búsqueda/filtros; pruebas de errores, permisos y estados vacíos; revisión UI.

## Criterios confirmados para esta entrega (22/10/2026)
- Se permiten expedientes repetidos hasta definir su ámbito de unicidad; no imponer unicidad global.
- Tipo/modalidad, agrupamiento, categoría y tramo se registran como texto libre, sin catálogos nuevos.
- Los datos mínimos enumerados son obligatorios. Los campos complementarios quedan fuera de esta fase.
- Permisos Django separados para consultar, crear, editar datos y cambiar estado/situación; no se crean roles de negocio.
- No hay eliminación de concursos en esta fase. «CRUD» se interpreta conforme al objetivo de alta, consulta y edición, preservando el historial.

La definición futura de catálogos, ámbito de unicidad y campos complementarios no se considera resuelta por esta implementación.

## Ajustes autorizados tras pruebas de SDD-003 (23/10/2026)
- El expediente usa `99-NNNN-9999`: bloques primero/final de 2/4 dígitos; el central tiene longitud variable, entre 1 y 9999, sin relleno. Validar en Django y frontend mediante componentes compartidos.
- Se mantiene la ausencia de unicidad: guardar expedientes repetidos entre concursos con advertencia.
- Funciones del cargo pasa a ser opcional en modelo y formulario, en un desplegable de datos adicionales. Conservar el campo, el contenido existente y su disponibilidad documental; no copiar la denominación.
- La migración no reescribe identificadores ni funciones. Permitir conservar un expediente histórico fuera de formato en la edición del mismo registro; exigir el formato nuevo si cambia.
- Mantener permisos, historial y controles de concurrencia. Estos ajustes sustituyen únicamente la obligatoriedad y el formato antes indicados; no habilitan SDD-004.

## Consolidación de catálogos autorizada (23/10/2026)
- Sustituye el texto libre de modalidad y clasificación: tipo de concurso obligatorio con `TextChoices` (Cerrado Interno, Cerrado General, Abierto, Acotado), sin tabla de modalidades.
- Referencias: Ordenanza 33/10-CS y Ordenanza 37/25-CS, Anexo, art. 14. Acotado pertenece al procedimiento especial de regularización de personal Nodocente con ATF; si procede la impugnación de la regularización comprende a los impugnantes y a la persona impugnada. La UI muestra la referencia al seleccionarlo y en la ficha correspondiente. No determina admisibilidad, aspirantes ni requisitos; la situación Impugnado no cambia la modalidad.
- Catálogo local versionado de los ocho códigos institucionales UNSJ, tomado de CoPla (`datos/agrupamientos_iniciales.json`, `cargos/normativa.py`, decisión DEC-054 y sus pruebas). Categorías dependientes y tramo derivado según la matriz documentada en DECISIONES. Sin conexión ni dependencia de CoPla y sin ABM nuevo.
- Una fuente local para las reglas de clasificación: Python valida y entrega a JS las opciones resueltas. Al cambiar agrupamiento se conserva categoría si sigue habilitada; en caso contrario se limpia categoría y tramo. Django rechaza combinaciones inválidas aunque se eluda JS. Tramo se presenta como información, sin entrada editable.
- Edición conserva selecciones y controles de versión/bloqueo. No altera denominación, funciones, CP, estructura, estados, historial ni reglas de participantes.
- Migración atómica: preflight completo; convertir solo correspondencias inequívocas y conservar los cuatro textos originales en `clasificacion_anterior`, no editable. Ante modalidad, agrupamiento o clasificación desconocidos/ambiguos, detener sin conversiones parciales y requerir revisión administrativa. No elegir un código por defecto. La reversión restaura originales únicamente si no hubo una corrección posterior.
- Aceptación: cuatro modalidades y rechazo de otras, toda la matriz y sus excepciones, edición, POST manipulado, preflight/migración/reversión sin pérdida, permisos, suite PostgreSQL y UI a 360/768/1280. No autoriza SDD-004.
