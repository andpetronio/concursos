# Producto: Sistema de Gestión de Concursos Nodocentes (UNSJ)

Estado: decisiones funcionales acordadas para el diseño inicial, sujetas a evolución controlada.

## Objetivo
Facilitar el trabajo de la Dirección de Concursos Nodocentes: registrar concursos, participantes, estado y control documental del expediente; generar documentos administrativos DOCX editables. El expediente oficial continúa fuera de la aplicación.

## Datos de un concurso
- Expediente y tipo de concurso.
- Cargo: denominación/funciones, agrupamiento, categoría, tramo, código presupuestario.
- Unidad, dependencia y cadena de dependencias; otros datos que necesiten las plantillas (lugar/horario, requisitos y temario), conforme se definan.
- La información del cargo se conserva como instantánea del concurso: cambios futuros de la estructura organizativa no alteran automáticamente el registro histórico.
- Los datos generales no requieren indicación de fojas.

## Participantes
- Jurado: 3 representaciones (autoridad de dependencia convocante, Rectorado y personal de dependencia), cada una con titular y suplente. Registrar persona, DNI, título, cargo, correo y teléfono; registrar reemplazos sin borrar historia cuando se implemente.
- Veedor: siempre representa a APUNSJ. Datos personales y de contacto. La designación/presencia es opcional; la solicitud de veedor debe poder emitirse y controlarse. Su ausencia no bloquea el trámite.
- Aspirantes: nombre, apellido y DNI. Se incorporan al recibir el acta de inscriptos. DNI único dentro de un concurso, reutilización de persona en diferentes concursos. Se podrá identificar luego al ganador.

## Control documental
- Los documentos previos a convocatoria pueden llegar en cualquier orden. La generación de PROYECTO de resolución de convocatoria requiere los CINCO requisitos: propuesta de jurado titular/suplente por dependencia (con foja), por Rectorado (con foja), por personal de la dependencia (con foja), afectación presupuestaria (con foja), certificación de vacancia (sin foja). También deben estar completos los datos requeridos de cargo/jurado.
- El checklist admite check, fecha, responsable, observaciones y referencia de foja cuando corresponda: por ejemplo `5` o `5/8`. Check y foja exigida son condiciones distintas.
- Después del acta de inscriptos, el orden es recomendado, no un bloqueo rígido.

### Checklist habitual (happy path)
1. Propuesta de jurados por autoridad de dependencia — foja.
2. Propuesta de jurados por Rectorado — foja.
3. Propuesta/elección de jurados por personal de dependencia — foja.
4. Afectación presupuestaria — foja.
5. Certificación de vacancia — sin foja.
6. Constancia de publicación de resolución de convocatoria — sin foja.
7. Acta de inscriptos — foja.
8. Constancia de envío del acta de inscriptos — sin foja.
9. Constancia de entrega de documentación al jurado — sin foja.
10. Acta de valoración de antecedentes — foja.
11. Nota del jurado con fecha de sorteo de temas y prueba de oposición — foja.
12. Acta de sorteo de temas — foja.
13. Tres temas de examen — sin foja.
14. Planilla de asistencia a oposición — sin foja.
15. Acta de prueba de oposición — foja.
16. Dictamen del jurado — foja.
17. Constancia de comunicación del dictamen a los aspirantes — sin foja.
18. Resolución de aprobación del dictamen — foja.
19. Resolución de designación — foja.

Las situaciones extraordinarias (impugnaciones, excusaciones, suspensiones, concurso desierto, etc.) se diseñarán después. No se ocultan ni se dan por resueltas automáticamente.

## Estados y actuaciones
- Estados principales previstos: `Preparación`, `Convocado`, `En curso`, `Con dictamen`, `Finalizado`.
- `Impugnado` y `Suspendido` son situaciones administrativas adicionales, no necesariamente sustituyen al estado principal.
- Estado modificable manualmente por usuario autorizado, con historial de quién/cuándo y justificación opcional.
- El sistema podrá SUGERIR cambios de estado a partir de actuaciones (p. ej. resolución de convocatoria registrada -> `Convocado`, dictamen registrado -> `Con dictamen`), pero nunca aplicarlos sin confirmación.
- No confundir estado del trámite con completitud documental.

## Documentos editables
- Todos los documentos producidos por el sistema deben poder descargarse en DOCX editable.
- Previstos: proyecto de resolución de convocatoria, oficio a APUNSJ solicitando veedor, notificaciones individuales a jurados, acta de sorteo de temas, proyecto de aprobación del dictamen, proyecto de designación.
- Una plantilla/proyecto generado NO equivale a un documento oficial incorporado al expediente. Número, fecha, foja y acto emitido se registrarán por separado.

## Integraciones con CoPla — PENDIENTES
- Inscripción: buscar persona por DNI, recuperar cargo de revista y validar requisitos (en particular relación jerárquica entre categorías; categoría 1 es superior a 7). Validaciones deben respetar modalidad, antigüedad y fecha de referencia cuando se especifique.
- Designación: consultar impacto en CoPla de resolución emitida; puede producir múltiples novedades (nueva designación, limitación de designación anterior, ATF encadenadas), siempre con respaldo jurídico y validación administrativa.
- No desarrollar estas integraciones ni acceder a la base de CoPla en las primeras fases. No asumir cambios automáticos de planta.

## Alcance de entregas
- Fase 0: fundaciones, identidad visual compartida, auth y timeout real a 30 min.
- Fase 1: concursos, CRUD, ficha y estados con historial.
- Fase 2: jurados, veedores y aspirantes.
- Fase 3: checklist y reglas de habilitación documental.
- Fase 4: DOCX editables.
- Fase futura: integración CoPla, ramas excepcionales y reglas especiales revisadas con normativa.

## Fuentes normativas y modelos de referencia para fases posteriores
- Ordenanza 33/10-CS, texto actualizado: reglamento de concursos.
- Ordenanza 6/14-R: circuito administrativo.
- Modelos aportados: proyecto de convocatoria, aprobación de dictamen, designación, solicitud de elecciones del personal y notificación a jurados.
- No inferir que un modelo aislado modifica lo establecido en la normativa. Confirmar ambigüedades antes de codificar reglas rígidas.

## Notificaciones y situación administrativa
- Tras el dictamen, controlar **constancia de comunicación del dictamen a los aspirantes** como requisito del checklist antes de la resolución de aprobación; fecha de última comunicación útil para el plazo, sujeto a reglas que se definan.
- Los estados son independientes del checklist; la aplicación puede sugerir cambios al registrar actuaciones, pero el operador confirma o modifica manualmente y queda historial.
- Los datos de contacto de jurados y veedores son correo electrónico y teléfono. Veedores siempre representan a APUNSJ; no pedir entidad representada.

## Regla de interoperabilidad proyectada
- Una resolución de designación puede originar varias novedades en CoPla; el sistema de Concursos **no** decide ni registra por sí solo limitaciones/ATF. CoPla analiza y exige actos administrativos y aprobación para ejecutar novedades.
- La validación futura por DNI para concursos cerrados considera jerarquía invertida del escalafón (categoría 1 superior a categoría 7) y no bloquea automáticamente sin revisión administrativa.
