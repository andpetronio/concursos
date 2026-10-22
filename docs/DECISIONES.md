# Registro de decisiones y pendientes

## Acordado
- Aplicación independiente de CoPla, destinada a Dirección de Concursos Nodocentes de la UNSJ.
- Identidad visual **Blanco y naranja**, con tokens fijos de `docs/DISEÑO.md`.
- Criticidad máxima de consistencia visual, reutilización y buenas prácticas Django.
- Autenticación con cierre por 30 minutos sin actividad real y respaldo en servidor.
- Estados principales y situaciones independientes; cambios sugeridos, jamás automáticos, y cambio manual con historial.
- Jurados: titular/suplente de tres representaciones. Veedores: APUNSJ, no bloquean trámite. Aspirantes: nombre, apellido, DNI.
- Cinco requisitos previos que habilitan el **proyecto** de resolución de convocatoria, sin importar el orden de llegada.
- Checklist habitual de 19 requisitos, con foja solo donde se indicó.
- DOCX editable y separación de proyecto, documento oficial y check del expediente.
- Dos integraciones futuras CoPla; la aplicación funciona sin ellas.

## Pendiente de validación antes de fases correspondientes
- Obligatoriedad exacta de campos adicionales de convocatoria y alcance de unicidad de expediente.
- Catálogos de modalidades, agrupamientos y permisos/roles de operación.
- Casos extraordinarios (impugnaciones, suspensión, recusación, sustitución, desierto, anulaciones) y sus actuaciones.
- Fechas/hitos de notificación del dictamen y sus plazos, a considerar en checklist operativo.
- ¿Cuándo se considera administrativamente «Finalizado»? Resolución emitida vs toma de posesión/cierre.
- Modelo definitivo de personas y fotografía histórica para documentos.
- Disponibilidad y naturaleza editables de las plantillas: se aportaron PDF que deben recrearse/verificarse como DOCX.
- Contrato API con CoPla, ejecución atómica o secuencial de múltiples movimientos y actos habilitantes.

No convertir estos pendientes en reglas definitivas sin nueva decisión administrativa.

## SDD-002 — Criterios confirmados por el usuario (22/10/2026)
- Expedientes repetidos permitidos mientras no se defina el ámbito de unicidad.
- Datos mínimos de la especificación obligatorios; tipo/modalidad, agrupamiento, categoría y tramo como texto libre. Sin campos complementarios en esta fase.
- Permisos nativos separados para consulta, alta, edición de datos y cambios manuales de estado/situación, sin roles nuevos ni eliminación de concursos.
- Los pendientes de catálogos, unicidad futura y campos complementarios siguen abiertos para una decisión posterior.
