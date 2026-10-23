# SDD-004 — Checklist documental, fojas y actuaciones

**Estado:** implementación verificada y entregada; pendiente de aceptación funcional. Ejecución autorizada expresamente por el usuario el 23/10/2026. SDD-001/002/003 y ajustes previos aceptados. No autoriza SDD-005.

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
| 7 | Oficio a APUNSJ solicitando veedor | No |
| 8 | Notas de notificación a jurados (check general para los seis titulares y suplentes) | No |
| 9 | Acta de inscriptos | Sí |
| 10 | Constancia de envío del acta de inscriptos | No |
| 11 | Constancia de entrega de documentación al jurado | No |
| 12 | Acta de valoración de antecedentes | Sí |
| 13 | Nota del jurado con fecha del sorteo de temas y prueba de oposición | Sí |
| 14 | Acta de sorteo de temas | Sí |
| 15 | Tres temas de examen | No |
| 16 | Planilla de asistencia a la prueba de oposición | No |
| 17 | Acta de prueba de oposición | Sí |
| 18 | Dictamen del jurado | Sí |
| 19 | Constancia de comunicación del dictamen a los aspirantes | No |
| 20 | Resolución de aprobación del dictamen | Sí |
| 21 | Resolución de designación | Sí |

## Reglas
- Convocatoria incluye publicación, oficio a APUNSJ y notas de notificación a jurados, en ese orden de presentación. Los tres son obligatorios según la etapa activa y pueden incorporarse en cualquier orden. Los dos nuevos no requieren foja; el check de notificaciones acredita el conjunto correspondiente a los seis jurados, sin controles individuales.
- La ausencia de veedor designado sigue sin bloquear el avance. El oficio de solicitud sí es un control documental obligatorio de Convocatoria; no integra los cinco previos para habilitar el proyecto. Generar un documento en SDD-005 no marcará automáticamente su requisito.
- Los cinco primeros pueden incorporarse en **cualquier orden**. Para habilitar **generación del PROYECTO** de convocatoria, todos marcados y fojas completadas donde corresponda, más datos de cargo y seis jurados identificados.
- Después de acta de inscriptos, mostrar secuencia orientativa, no bloquear checks fuera de orden.
- Validar fojas como `5` o `5/8` y guardar como texto. Una foja malformada o ausente NO da por completo un requisito que la exige.
- El check acredita documentación del expediente; no genera proyectos ni registra por sí solo un acto oficial emitido. La identificación de actos oficiales y la generación quedan para su fase autorizada.
- La constancia de comunicación del dictamen antecede a la resolución de aprobación en el camino ordinario; fecha y vencimientos especiales requieren revisión adicional.
- Sugerir «Con dictamen» solo ante dictamen verificado con fojas válidas si el estado actual es Preparación, Convocado o En curso. Nunca cambiar automáticamente, retroceder desde Con dictamen/Finalizado ni proponer Finalizado. Confirmación mediante formulario y permiso independiente existentes, con historial. No inferir convocatoria oficial del check de publicación.
- Los documentos extraordinarios se gestionarán en evolución propia, sin falsear que no existen.

## Aceptación
Tests de completa/incompleta y validación de foja, concurrencia básica de checks, cambios fuera de orden, sugerencia versus confirmación de estado e historial de usuario. UI compartida con contador y pendientes sin indicar incumplimiento por documentos aún no exigibles.

## Etapa documental y exigibilidad (decisión expresa del usuario)
- Selección manual de etapa activa entre las cinco secciones. Los requisitos de la etapa elegida y las anteriores son exigibles; los pendientes de etapas posteriores se muestran como No registrado, sin incumplimientos ni plazos inventados.
- Inicializar concursos anteriores y nuevos en Preparación de convocatoria, sin deducir avance de estado, participantes o documentación previa. El operador puede avanzar o retroceder la selección; no se pierden checks ni referencias.
- Etapa independiente del estado administrativo, con permiso documental, versión obligatoria, bloqueo y bitácora de antes/después, responsable y fecha.
- Mostrar completos / pendientes exigibles / etapas futuras por separado. Un check con foja pendiente conserva ese estado visible; check sin foja exigida no integra los completos.

## Persistencia, seguridad y servicios
- Catálogo estable de 21 requisitos en `expedientes/catalogo.py`, agrupación/orden/exigencia de foja centralizados. «Tres temas» es un único control. Unicidad concurso/requisito y restricción del identificador en base de datos.
- Inicializar explícitamente desde el servicio transaccional de alta y por migraciones para concursos anteriores. La ampliación de 19 a 21 agrega únicamente los dos controles faltantes mediante migraciones nuevas; preserva PK, checks, fojas, observaciones, responsables, versiones, etapa y bitácoras anteriores. Nunca escribir durante una consulta GET.
- Fojas: texto positivo individual/rango ascendente, espacios exteriores o alrededor de `/` normalizados; rechazar letras, decimales, cero y rangos inversos. Guardar un check sin foja permite una carga parcial y permanece incompleto. No mostrar ni aceptar campos de foja donde no corresponden.
- Correcciones y desmarcados conservan instantáneas antes/después con actor, fecha y versión. Al desmarcar queda la última verificación histórica, diferenciada de la última modificación. No-op no fabrica un evento.
- Consulta e historiales: `concursos.view_concurso`. Escritura de check/fojas/observaciones/etapa: además `expedientes.change_controldocumental`. No asignar permisos automáticamente ni exponer altas, eliminaciones o edición de bitácoras.
- POST/CSRF, sesión real de 30 minutos y búsquedas anidadas por concurso; permisos también dentro de los servicios de escritura. Lock por control/seguimiento más versión, sin interferir con edición general/participantes.
- `consultar_documentacion(concurso, controles=None, jurados=None)` devuelve controles ordenados, verificados, completos, fojas, pendientes globales/exigibles/futuros, advertencias, sugerencia y habilitación. `habilitacion_convocatoria` explica documentos, jurados o datos generales faltantes; disponible para SDD-005 sin generar documentos.
- Advertir secuencia pendiente sin bloquear. La aprobación sin comunicación del dictamen debe mostrar aviso visible y permitir guardar.

## Límites y evidencia
Sin generación DOCX/PDF, integración CoPla, circuitos extraordinarios, cambios en participantes o nuevos estados administrativos. No eliminación de datos, commit, push ni despliegue. Migraciones verificadas en base de pruebas; aplicación sobre base persistente es operación posterior.

Ver `docs/SDD-004-EVIDENCIA.md` para comandos, resultados, revisión visual y hallazgos independientes. Al cerrar, detenerse pendiente de aceptación funcional del usuario.
