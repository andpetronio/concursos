# SDD-003 — Participantes institucionales y aspirantes

**Estado:** Implementación entregada; aceptación del usuario pendiente. Ver `docs/SDD-003-EVIDENCIA.md`.

## Objeto
Relacionar personas con concursos como jurados, veedores o aspirantes sin duplicar personas.

## Jurados
Por concurso: autoridad de dependencia convocante, Rectorado y personal de dependencia; un titular y un suplente por cada representación. Guardar nombre, apellido, DNI, título, unidad, email y teléfono. La unidad es obligatoria en alta y edición y representa el destino organizativo donde presta servicios el integrante, que puede diferir de la dependencia del cargo concursado. Se conserva como texto propio de esa participación, no como atributo global de Persona ni referencia mutable a la unidad del concurso. Cargo deja de exigirse y de ser entrada del formulario; su dato anterior se conserva y se consulta en la ficha. Diferenciar registro de la persona de su asignación al jurado; sustituciones y vigencia requieren diseño antes de implementarlas.

## Veedores
Representan **siempre a APUNSJ**. No mostrar selector de institución. Nombre, apellido, DNI, cargo si corresponde, email y teléfono. La ausencia de veedor designado o su inasistencia NO bloquean el concurso; el oficio de solicitud a APUNSJ se contempla en documentos/checklist.

## Aspirantes
Cargar cuando la Dirección recibe el **acta de inscriptos**: nombre, apellido y DNI. DNI no duplicado dentro del mismo concurso; la misma persona puede ser aspirante en múltiples concursos. Preparar vínculo a ganador para fase de dictamen/designación, sin puntajes o evaluación compleja de primera versión.

## Integración futura (no ejecutar)
Consulta por DNI a CoPla para nombre y cargo de revista, y eventual validación de categoría jerárquica/ámbito/planta permanente; sin dependencia operativa inicial. Una categoría numéricamente menor implica jerarquía mayor (1 > 7). Validar por modalidad y fecha de referencia; no bloquear automáticamente por discrepancias.

## Aceptación
Participantes asignados por concurso con validaciones y permisos, prueba de DNI duplicado/localidad, reutilización de persona; UI coherente y sin información duplicada innecesaria.

## Ajustes autorizados tras pruebas de carga (23/10/2026)
- Agregar `email` y `expediente_inscripcion` a Aspirante, ambos opcionales inicialmente, vacíos en inscripciones anteriores; nunca a Persona. Disponibles para alta, consulta y edición de esa inscripción.
- Correo con validación Django de email. Expediente con formato compartido `99-NNNN-9999` (2 dígitos, entero 1–9999 sin relleno, 4 dígitos). Sin restricciones de unicidad de expediente nuevas.
- Todos los DNI usan el campo/máscara compartido: 8 dígitos ASCII, entrada `text` con `inputmode="numeric"`, visual `99.999.999`, pegado con/sin puntos, normalización antes de búsquedas/comparaciones y preservación de ceros iniciales. Validación Django independiente de JS.
- No transformar datos históricos en la migración: conservar valores anteriores sin cambios al editar otros datos; toda alta o modificación de identificador exige el formato nuevo. No reducir el tamaño de la columna DNI ni colisionar identidades existentes.
- La edición de inscripción usa los mismos permisos de edición de concurso, versión obligatoria y bloqueo de fila que las otras participaciones. Una inscripción no puede sobrescribir otra ni la identidad compartida.
- Verificar migración con registros de la versión anterior, alta/edición/consulta, emails inválidos, unicidad previa, concurrencia y formularios a 360/768/1280 px. No avanzar a control documental.

## Consolidación complementaria de datos del concurso (23/10/2026)
La modalidad y clasificación del cargo se consolidan conforme al apartado de catálogos de SDD-002. No se cambian las reglas, permisos ni datos de jurados, veedores o aspirantes. Acotado es una selección informativa: no agrega participantes ni valida su admisibilidad. SDD-004 sigue fuera de alcance.

## Ajuste puntual de jurados: Unidad en lugar de Cargo (23/10/2026)
- Alta y edición requieren Unidad, con la misma definición compartida del campo. Título, DNI, correo, teléfono, representación y calidad (titular/suplente) mantienen sus reglas.
- Migración aditiva: agregar unidad vacía a jurados anteriores, sin inferirla del cargo ni de la dependencia del concurso. Conservar cargo y volverlo opcional. Completar unidad al editar un jurado anterior; la ficha distingue ese dato pendiente y sigue mostrando el cargo histórico si existe.
- Conservar unidad por concurso: registrar o corregir la participación en otro concurso no cambia la anterior. Mantener permisos, plaza única, responsables/fechas y edición con bloqueo/versión.
- No modificar aspirantes ni veedores. Probar alta/edición con unidad obligatoria sin cargo, conservación del cargo y restantes datos, independencia entre concursos, migración con registros anteriores y rechazo de ediciones desactualizadas. Revisión focalizada y UI con componentes existentes; sin SDD-004.
