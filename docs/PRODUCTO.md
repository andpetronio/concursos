# Producto: Sistema de Gestión de Concursos Nodocentes (UNSJ)

Estado: decisiones funcionales acordadas para el diseño inicial, sujetas a evolución controlada.

## Objetivo
Facilitar el trabajo de la Dirección de Concursos Nodocentes: registrar concursos, participantes, estado y control documental del expediente; generar documentos administrativos DOCX editables. El expediente oficial continúa fuera de la aplicación.

## Datos de un concurso
- Expediente y tipo obligatorio de concurso: Cerrado Interno, Cerrado General, Abierto o Acotado.
- Cargo: denominación, agrupamiento, categoría, tramo, código presupuestario. Funciones es información complementaria opcional, conservada para futuras plantillas, sin copiar automáticamente la denominación.
- Unidad, dependencia y cadena de dependencias; otros datos que necesiten las plantillas (lugar/horario, requisitos y temario), conforme se definan.
- La información del cargo se conserva como instantánea del concurso: cambios futuros de la estructura organizativa no alteran automáticamente el registro histórico.
- Los datos generales no requieren indicación de fojas.

### Clasificación del cargo y modalidad (consolidación SDD-002/003)
- Agrupamiento desde catálogo local por código institucional UNSJ: 01, 2A, 2B, 03, 4A, 4B, 4C y 4D. La categoría se selecciona entre las habilitadas para ese código; el tramo se calcula automáticamente. La matriz verificada en CoPla consta en DECISIONES. No existe conexión con su base ni dependencia de ejecución entre proyectos.
- Al cambiar agrupamiento se mantiene categoría si sigue siendo válida; de lo contrario se limpian categoría y tramo. Django realiza la validación definitiva y conserva los valores al editar.
- Los tres tipos ordinarios se referencian en la Ordenanza 33/10-CS. Acotado se fundamenta en la [Ordenanza 37/25-CS, Anexo, artículo 14](https://digesto.unsj.edu.ar/admin/digesto_admin/pdf/ORD37O-2512511.pdf#page=8), dentro del procedimiento especial de regularización del personal Nodocente con ATF: cuando resulta procedente la impugnación de una regularización, comprende a los impugnantes y a la persona impugnada. Seleccionarlo muestra información normativa; no activa admisibilidad, incorporaciones automáticas ni requisitos documentales. Una situación Impugnado no convierte el concurso en Acotado.
- Migración conservadora: convertir correspondencias inequívocas, preservar los textos originales y detener toda la migración ante valores desconocidos o ambiguos, para revisión administrativa. No se reemplazan por una opción arbitraria.

## Participantes
- Jurado: 3 representaciones (autoridad de dependencia convocante, Rectorado y personal de dependencia), cada una con titular y suplente. Registrar persona, DNI, título, unidad de servicio obligatoria, correo y teléfono. La unidad corresponde a cada participación histórica y puede diferir de la dependencia del cargo concursado; no se infiere de ella. Cargo deja de exigirse, conservando los valores anteriores visibles en la ficha. Los jurados anteriores quedan con unidad pendiente de completar al editar. Registrar reemplazos sin borrar historia cuando se implemente.
- Veedor: siempre representa a APUNSJ. Datos personales y de contacto. La designación/presencia es opcional; la solicitud de veedor debe poder emitirse y controlarse. Su ausencia no bloquea el trámite.
- Aspirantes: nombre, apellido y DNI. Cada inscripción también conserva correo electrónico y expediente de inscripción opcionales, disponibles en alta, edición y consulta; pertenecen al vínculo aspirante-concurso, sin modificar los de otra inscripción de la misma persona. Se incorporan al recibir el acta de inscriptos. DNI único dentro de un concurso, reutilización de persona en diferentes concursos. Se podrá identificar luego al ganador.

## Identificadores y entrada de datos (ajustes SDD-003, 23/10/2026)
- DNI nuevo o corregido: exactamente 8 dígitos ASCII, guardado como texto sin separadores y presentado en los campos como `99.999.999`; preservar ceros iniciales. El pegado con o sin puntos identifica a la misma persona. Se conservan los separadores de entrada admitidos anteriormente para compatibilidad.
- Expedientes del concurso e inscripción: `99-NNNN-9999`, con primer bloque de 2 dígitos, central entre 1 y 9999 sin ceros de relleno y final de 4 dígitos. No se agrega unicidad; expediente repetido entre concursos se guarda con advertencia.
- No se reescriben identificadores históricos ni se completan sus ceros automáticamente. Un valor anterior fuera de formato puede conservarse al editar otros datos del registro; cambiarlo exige el nuevo formato. La excepción no habilita altas con valores fuera de formato.
- Máscaras compartidas y validación de servidor; correo mediante validación de email. Teléfono sin máscara y fechas con control de fecha cuando corresponda. Los controles de versión y bloqueos existentes se mantienen.

## Control documental
- Los documentos previos a convocatoria pueden llegar en cualquier orden. La generación de PROYECTO de resolución de convocatoria requiere los CINCO requisitos: propuesta de jurado titular/suplente por dependencia (con foja), por Rectorado (con foja), por personal de la dependencia (con foja), afectación presupuestaria (con foja), certificación de vacancia (sin foja). También deben estar completos los datos requeridos de cargo/jurado.
- El checklist admite check, fecha, responsable, observaciones y referencia de foja cuando corresponda: por ejemplo `5` o `5/8`. Check y foja exigida son condiciones distintas.
- Después del acta de inscriptos, el orden es recomendado, no un bloqueo rígido.
- SDD-004 implementa los 21 requisitos ordinarios en cinco secciones de la ficha. Cada concurso nuevo o anterior recibe los controles sin verificaciones ficticias. Hay historial de correcciones antes/después, responsable y fecha; versión obligatoria y bloqueo evitan sobrescrituras concurrentes.
- En Convocatoria, inmediatamente después de publicación, son obligatorios el oficio a APUNSJ solicitando veedor y las notas de notificación a jurados. Se incorporan en cualquier orden y sin foja; el segundo es un check general de las notificaciones correspondientes a los seis jurados. No se exige que haya veedor designado. Generar esos documentos en SDD-005 no marcará los controles automáticamente. La ampliación agrega solo los dos controles faltantes, sin sobrescribir registros o historial.
- La etapa documental activa se elige manualmente entre Preparación de convocatoria, Convocatoria, Inscripciones, Antecedentes y oposición, Dictamen y finalización. Los requisitos de esa etapa y de las anteriores son exigibles; los de etapas futuras no registrados se muestran de forma neutral. La selección inicia en Preparación, tiene historial propio y puede corregirse sin borrar controles. Nunca se deduce del estado administrativo ni determina vencimientos.
- El resumen distingue completos, pendientes exigibles y etapas futuras. La preparación requiere los cinco checks, cuatro fojas válidas, seis plazas de jurado identificadas con los datos requeridos existentes y datos generales válidos. Se informa qué falta, sin bloquear la carga de documentación posterior.
- Fojas individuales o rangos positivos ascendentes; normalizar espacios y rechazar referencias inválidas. Un check sin la foja exigida puede guardarse como carga parcial y sigue pendiente. Los requisitos sin foja no muestran ese campo.
- Al registrar aprobación sin comunicación del dictamen se advierte de forma visible, permitiendo guardar. Un dictamen completo puede sugerir Con dictamen; confirmación y permiso de estado son independientes. No se propone Finalizado ni se interpreta un check como acto oficial emitido.
- Consulta e historiales con `concursos.view_concurso`; escritura documental y selección de etapa requieren además `expedientes.change_controldocumental`, sin asignación automática a cuentas. Los historiales y requisitos no se eliminan desde la aplicación.
- Servicios de consulta y habilitación disponibles para SDD-005. SDD-004 no genera documentos, identifica actos oficiales ni desarrolla circuitos extraordinarios. El usuario aceptó SDD-001 a SDD-004 y autorizó expresamente SDD-005 el 23/10/2026.

### Checklist habitual (happy path)
1. Propuesta de jurados por autoridad de dependencia — foja.
2. Propuesta de jurados por Rectorado — foja.
3. Propuesta/elección de jurados por personal de dependencia — foja.
4. Afectación presupuestaria — foja.
5. Certificación de vacancia — sin foja.
6. Constancia de publicación de resolución de convocatoria — sin foja.
7. Oficio a APUNSJ solicitando veedor — sin foja.
8. Notas de notificación a jurados — sin foja; un check para las notificaciones de los seis titulares y suplentes.
9. Acta de inscriptos — foja.
10. Constancia de envío del acta de inscriptos — sin foja.
11. Constancia de entrega de documentación al jurado — sin foja.
12. Acta de valoración de antecedentes — foja.
13. Nota del jurado con fecha de sorteo de temas y prueba de oposición — foja.
14. Acta de sorteo de temas — foja.
15. Tres temas de examen — sin foja.
16. Planilla de asistencia a oposición — sin foja.
17. Acta de prueba de oposición — foja.
18. Dictamen del jurado — foja.
19. Constancia de comunicación del dictamen a los aspirantes — sin foja.
20. Resolución de aprobación del dictamen — foja.
21. Resolución de designación — foja.

Las situaciones extraordinarias (impugnaciones, excusaciones, suspensiones, concurso desierto, etc.) se diseñarán después. No se ocultan ni se dan por resueltas automáticamente.

## Estados y actuaciones
- Estados principales previstos: `Preparación`, `Convocado`, `En curso`, `Con dictamen`, `Finalizado`.
- `Impugnado` y `Suspendido` son situaciones administrativas adicionales, no necesariamente sustituyen al estado principal.
- Estado modificable manualmente por usuario autorizado, con historial de quién/cuándo y justificación opcional.
- El sistema podrá SUGERIR cambios de estado a partir de actuaciones (p. ej. resolución de convocatoria registrada -> `Convocado`, dictamen registrado -> `Con dictamen`), pero nunca aplicarlos sin confirmación.
- No confundir estado del trámite con completitud documental.

## Documentos editables
- Todos los documentos producidos por el sistema deben poder descargarse en DOCX editable.
- Previstos: proyecto de resolución de convocatoria, oficio a APUNSJ solicitando veedor, notificaciones individuales a jurados, nota para elección de representantes del personal, proyecto de aprobación del dictamen, proyecto de designación.
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

### SDD-005: entrega documental recuperada (aceptación pendiente)
- Seis tipos implementados desde datos verificables: cinco PDF originales disponibles e inspeccionados, más APUNSJ provisional. Complementos críticos requeridos por tipo; su falta bloquea generación, sin placeholders. Seis notas individuales se conservan y descargan también como ZIP histórico. No se presume fidelidad visual Word sin validación.
- Mérito y persona propuesta para designación son expresos, no derivados del orden de inscripción. Presupuesto, hechos de actuaciones, normativa, autoridades y condiciones requieren datos acreditados; no se copian ejemplos como ciertos.
- APUNSJ: destinatario institucional acotado y configurable por permiso específico, tratamiento/cargo coherentes y título opcional. El oficio es siempre BORRADOR NO EMITIDO, sin lugar, fecha, número ni firmante inventados; esos datos se indican como no incorporados. Acotado requiere revisión administrativa explícita.
- Generar y descargar requiere permiso documental y consulta de concurso. Se conservan bytes, hash, plantilla versionada, datos usados y actor/fecha; cambios posteriores de concurso o autoridad no alteran antecedentes. Ninguna generación modifica el procedimiento administrativo ni completa controles. Ver `SDD-005-EVIDENCIA.md` para pendientes de aceptación.
