# SDD-003 — Participantes institucionales y aspirantes

**Estado:** Implementación entregada; aceptación del usuario pendiente. Ver `docs/SDD-003-EVIDENCIA.md`.

## Objeto
Relacionar personas con concursos como jurados, veedores o aspirantes sin duplicar personas.

## Jurados
Por concurso: autoridad de dependencia convocante, Rectorado y personal de dependencia; un titular y un suplente por cada representación. Guardar nombre, apellido, DNI, título, cargo, email y teléfono. Diferenciar registro de la persona de su asignación al jurado; sustituciones y vigencia requieren diseño antes de implementarlas.

## Veedores
Representan **siempre a APUNSJ**. No mostrar selector de institución. Nombre, apellido, DNI, cargo si corresponde, email y teléfono. La ausencia de veedor designado o su inasistencia NO bloquean el concurso; el oficio de solicitud a APUNSJ se contempla en documentos/checklist.

## Aspirantes
Cargar cuando la Dirección recibe el **acta de inscriptos**: nombre, apellido y DNI. DNI no duplicado dentro del mismo concurso; la misma persona puede ser aspirante en múltiples concursos. Preparar vínculo a ganador para fase de dictamen/designación, sin puntajes o evaluación compleja de primera versión.

## Integración futura (no ejecutar)
Consulta por DNI a CoPla para nombre y cargo de revista, y eventual validación de categoría jerárquica/ámbito/planta permanente; sin dependencia operativa inicial. Una categoría numéricamente menor implica jerarquía mayor (1 > 7). Validar por modalidad y fecha de referencia; no bloquear automáticamente por discrepancias.

## Aceptación
Participantes asignados por concurso con validaciones y permisos, prueba de DNI duplicado/localidad, reutilización de persona; UI coherente y sin información duplicada innecesaria.
