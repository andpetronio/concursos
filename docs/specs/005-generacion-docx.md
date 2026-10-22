# SDD-005 — Generación de documentos DOCX editables

**Estado:** PROGRAMADA; no ejecutar hasta validar SDD-004 y las plantillas.

## Objetivo
Documentos administrativos editables construidos a demanda desde datos de concurso, jurados, aspirantes, fojas y resoluciones **ya registrados**.

## Documentos previstos
1. Proyecto de resolución de convocatoria y su Anexo.
2. Oficio solicitando veedor a APUNSJ.
3. Notas individuales notificando designación a cada jurado.
4. Acta de sorteo de temas.
5. Proyecto de resolución de aprobación del dictamen y orden de mérito.
6. Proyecto de resolución de designación.

## Reglas
- Archivo final **DOCX editable**; preservar formato institucional, títulos, considerandos, artículos, paginación y tablas relevantes con revisión humana.
- Los modelos aportados están en **PDF**; no suponer que existe una plantilla DOCX editable ya verificada. Reconstruir/validar cada plantilla en la fase correspondiente a partir de los originales.
- No producir en serio un proyecto con campos faltantes críticos o marcadores `{{...}}` sin resolver; reportar faltantes claramente.
- Distinguir proyecto generado de acto emitido (número/fecha) y requisito incorporado al expediente (check/foja).
- El usuario puede modificar el DOCX fuera de la app; nunca afirmar que el contenido posterior permanece sincronizado automáticamente.
- La generación de DOCX no notifica ni envía ni firma documentos.

## Aceptación
Tests de plantillas y placeholders, datos de prueba sin DNI reales, archivos DOCX abiertos/verificables, reglas de bloqueo en proyecto convocatoria, manejo de opcionales y revisión visual de documentos generados.
