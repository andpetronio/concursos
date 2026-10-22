# SDD-900 — Integraciones futuras con CoPla (SIN IMPLEMENTAR)

## Contexto
Concursos y CoPla son aplicaciones independientes. Concursos representa selección y actos del concurso. CoPla es autoridad técnica para planta, designaciones, vacancias y ATF.

## Interfaz A: inscriptos/aspirantes
Consulta por DNI, devuelve persona y cargo de revista en fecha de referencia. Validación orientativa de modalidad y nivel jerárquico (cat. 1 es jerárquicamente mayor que cat. 7), antigüedad y dependencia cuando se pueda. Divergencias requieren validación humana, no rechazo automático.

## Interfaz B: designación
Registrar resolución **oficial**, ganador, cargo concursado y fecha efectiva de posesión. Solicitar a CoPla **análisis previo** de cambios potenciales: nueva designación, eventual limitación de anterior cargo titular, limitación de ATF de ocupantes y cascada. Cada movimiento necesita su acto y autorización; una resolución no se presume suficiente para toda la cascada.

## Requisitos técnicos aún por definir
API autenticada, derechos de operación, snapshot, conciliación de persona por DNI y cargo por CP, idempotencia, reintentos, errores y transacciones, ejecución o propuesta de múltiples novedades; estrategia de confirmación administrativa. No acceder directamente a tablas de CoPla.
