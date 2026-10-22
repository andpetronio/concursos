# SDD-004 — Checklist documental, fojas y actuaciones

**Estado:** PROGRAMADA, no ejecutar todavía.

## Objetivo
Controlar integridad documental del expediente del concurso sin sustituirlo. Cada requisito tiene check, marca de tiempo, usuario, observaciones y foja cuando se indique.

## Checklist ordinario (orden sugerido)
| # | Requisito | ¿Foja requerida? |
|---|---|---|
| 1 | Indicación de jurado titular y suplente por dependencia convocante | Sí |
| 2 | Indicación de jurado titular y suplente por Rectorado | Sí |
| 3 | Indicación de jurado titular y suplente por personal de la dependencia | Sí |
| 4 | Afectación presupuestaria | Sí |
| 5 | Certificación de vacancia del cargo | No |
| 6 | Constancia de publicación de resolución de convocatoria | No |
| 7 | Acta de inscriptos | Sí |
| 8 | Constancia de envío del acta de inscriptos | No |
| 9 | Constancia de entrega de documentación al jurado | No |
| 10 | Acta de valoración de antecedentes | Sí |
| 11 | Nota del jurado con fecha del sorteo de temas y prueba de oposición | Sí |
| 12 | Acta de sorteo de temas | Sí |
| 13 | Tres temas de examen | No |
| 14 | Planilla de asistencia a la prueba de oposición | No |
| 15 | Acta de prueba de oposición | Sí |
| 16 | Dictamen del jurado | Sí |
| 17 | Constancia de comunicación del dictamen a los aspirantes | No |
| 18 | Resolución de aprobación del dictamen | Sí |
| 19 | Resolución de designación | Sí |

## Reglas
- Los cinco primeros pueden incorporarse en **cualquier orden**. Para habilitar **generación del PROYECTO** de convocatoria, todos marcados y fojas completadas donde corresponda, más datos de cargo y seis jurados identificados.
- Después de acta de inscriptos, mostrar secuencia orientativa, no bloquear checks fuera de orden.
- Validar fojas como `5` o `5/8` y guardar como texto. Una foja malformada o ausente NO da por completo un requisito que la exige.
- Registrar resolución oficial emitida separadamente de proyecto generado y de check documental.
- La constancia de comunicación del dictamen antecede a la resolución de aprobación en el camino ordinario; fecha y vencimientos especiales requieren revisión adicional.
- Sugerir (no imponer) cambios de estado por eventos: resolución oficial de convocatoria -> Convocado, dictamen incorporado -> Con dictamen, etc. El usuario siempre confirma; historial.
- Los documentos extraordinarios se gestionarán en evolución propia, sin falsear que no existen.

## Aceptación
Tests de completa/incompleta y validación de foja, concurrencia básica de checks, cambios fuera de orden, sugerencia versus confirmación de estado e historial de usuario. UI compartida con contador y pendientes sin indicar incumplimiento por documentos aún no exigibles.
