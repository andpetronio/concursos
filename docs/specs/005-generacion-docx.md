# SDD-005 — Generación de documentos DOCX editables

**Estado:** autorizada por pedido expreso del usuario (23/10/2026); implementación recuperada y ampliada, aceptación pendiente. Los cinco PDF originales están disponibles en `documentos/modelos/` y fueron inspeccionados; su reconstrucción Word requiere validación visual y administrativa. Este archivo conserva su nombre original: la referencia del pedido a `005-documentos.md` corresponde a esta especificación, no a una segunda spec.

## Objetivo y alcance autorizado
DOCX genuinos y editables a demanda, desde datos verificables registrados. Se distinguen borrador generado, documento emitido e incorporación verificada al expediente. Generar nunca firma, envía, notifica ni altera estado, controles, fojas, resoluciones oficiales o participantes.

Seis tipos: proyecto de convocatoria y anexo; seis notificaciones de jurados y ZIP; oficio a APUNSJ; proyecto de aprobación del dictamen; proyecto de designación; nota de solicitud de elección de representantes del personal. Esta última sustituye el acta de sorteo prevista originalmente: no se incorpora un séptimo documento.

## Entrega recuperada y fuentes disponibles
- Motor común de composición Word, catálogo de seis tipos y clasificación de variables automáticas, complementarias y pendientes.
- Oficio APUNSJ `apunsj-1`, basado exclusivamente en el encabezado y finalidad expresamente indicados en el pedido. Siempre **BORRADOR NO EMITIDO**: lugar, fecha, número de oficio y firmante quedan identificados como no incorporados, sin marcadores de plantilla ni datos inventados. No es un modelo institucional aprobado por fidelidad visual.
- Configuración acotada del destinatario: tratamiento, cargo coherente, título opcional, nombre y apellido. Permiso específico y versión para evitar sobrescritura. Encabezado Sr. Secretario General / Sra. Secretaria General de APUNSJ, nombre completo y Presente.
- Los cinco originales de `FUENTES.md` sustentan las plantillas `convocatoria-2`, `jurados-2`, `dictamen-2`, `designacion-2` y `elecciones-2`. Complementos críticos requeridos y datos existentes se revalidan antes de generar: no hay placeholders ni artículos vacíos. Las seis notas se guardan en un ZIP histórico, con manifiesto y hashes por miembro; descarga individual y de ZIP sin regenerar.
- Convocatoria consulta obligatoriamente `expedientes.services.habilitacion_convocatoria`, sin atajos: muestra requisitos previos, fojas, seis plazas y datos faltantes del concurso. No existe vía de generación que omita este control.
- Acotado requiere confirmación explícita de revisión administrativa; se identifica la ausencia de modelo específico aprobado. No se infieren consecuencias normativas.

## Datos, trazabilidad y seguridad
Datos existentes se revisan antes del POST sin volver a solicitarlos. Se revalidan datos y versiones del concurso, destinatario, personas, jurados, aspirantes y controles pertinentes, hash de fuente y versión de plantilla al generar mediante huella obligatoria de revisión y bloqueos. No se agregan campos al concurso. Cada generación guarda bytes DOCX, SHA-256, versión de plantilla, actor/fecha e instantánea inmutable del concurso, destinatario, complementos y actuaciones verificadas. Descargas devuelven exactamente esos bytes, sin regenerar ni cambiar con ediciones posteriores. Sin rutas arbitrarias, almacenamiento público o envío a terceros.

Generación y descarga requieren autenticación, `concursos.view_concurso` y `documentos.generar_documento`. La configuración requiere `documentos.configurar_institucion`. Sin otorgamiento automático de permisos. GET no genera; POST protegido por CSRF. Se conserva el control existente de sesión y todas las URLs se ubican bajo `/concursos/`.

## Aceptación pendiente
La aceptación requiere aprobar la reconstrucción institucional Word (VISTO, CONSIDERANDO, artículos, anexo de doce apartados, tablas presupuestarias agrupadas y saltos), abrir/renderizar muestras representativas y validar la redacción administrativa. Se conservan membrete sin firma y recibí editable en notas a jurados; no se reproducen firmas, conmemoraciones anuales ni autoridades de los ejemplos. Tratamientos de jurados y resoluciones oficiales no existen hoy como datos estructurados: no inferirlos de nombres, títulos o checklist. No seleccionar aspirante por orden de inscripción ni afirmar ausencia de impugnaciones/unanimidad/participación.

Pruebas y evidencia de recuperación en `../SDD-005-EVIDENCIA.md`. No declarar cumplida toda SDD-005 ni avanzar a otra fase.

## Datos complementarios y decisiones conservadoras
- Formularios por tipo, con textos acreditados requeridos para fundamento normativo exacto, hechos, inscripciones, requisitos, temario, comunicaciones y autoridades. No se agregan campos a Concurso. Tratamientos por jurado opcionales y expresos; no se deducen de nombres.
- Presupuesto con campos acreditados independientes para las trece columnas y sus detalles; no se copian códigos ni unidades de los ejemplos.
- Dictamen y designación requieren aspirantes y actuaciones verificadas que se citan; mérito introducido expresamente como `puesto | ID de aspirante`, sin IDs ajenos, puestos/personas duplicados ni orden implícito de inscripción. La lista de aspirantes y mérito no tiene un límite fijo de cinco/tres personas.
- Designación requiere elección expresa de aspirante del concurso y efectos acreditados. La limitación anterior es una decisión expresa; si corresponde exige texto íntegro y ajusta numeración. No hay efectos en CoPla.
- La numeración defectuosa de convocatoria (omite 4 y duplica 8) se normaliza a 1–8 manteniendo las ocho disposiciones existentes. La inconsistencia «Resolución/Ordenanza 6/14-R» no se resuelve jurídicamente por intuición: fundamento/circuito se suministran acreditados. Validación administrativa pendiente.
- El marco Acotado siempre requiere revisión expresa y texto normativo aplicable; no se añaden requisitos ordinarios de Cerrado Interno a otras modalidades.
