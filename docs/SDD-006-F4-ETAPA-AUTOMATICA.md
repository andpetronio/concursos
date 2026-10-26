# SDD-006 · Fase 4A · Avance automático de etapa documental

## Regla implementada

Al **registrar** el último de los cinco controles de Preparación de convocatoria como completo, la etapa documental cambia transaccionalmente de `preparacion` a `convocatoria`. Se comprueba cada requisito con el catálogo y sus fojas requeridas. **No** depende de que los jurados, los datos de convocatoria o los códigos PPAL/ACTIV estén listos para generar el proyecto: esa habilitación integral se informa por separado.

El estado administrativo («Convocado»), la resolución oficial, los archivos DOCX y los demás controles permanecen intactos.

## Seguridad e historial

El servicio bloquea primero `SeguimientoDocumental` y luego el control modificado; los guardados paralelos del mismo concurso quedan ordenados. El último guardado y la transición se registran en la **misma transacción**: si falla cualquier historial, todo se revierte. Cada evento de etapa tiene `origen` manual o automático y mantiene el usuario que completó el requisito final.

- Sin cambios de control, sin transición ni historial nuevo.
- Sin avance retroactivo al consultar concursos históricos con cinco controles completos.
- No retroceder de etapa al desmarcar documentación.
- Si un operador vuelve **manualmente** a Preparación, los nuevos controles no provocan reavances automáticos; cualquier avance posterior requiere una acción manual autorizada.
- La elección manual de etapas posteriores sigue disponible con sus permisos y versionado.
- El autoguardado actualiza etapa, contador y estado de requisitos exigibles usando la respuesta persistida del servidor.

## Verificaciones pendientes en la instalación Docker

La entrega incluye la migración aditiva `expedientes.0006_cambioetapadocumental_origen` y pruebas de transición, autoguardado AJAX, reversión por error de bitácora, no-op, respeto del retorno manual y concurrencia de los últimos dos controles. Ejecutar `migrate --plan`, respaldo y migración, pruebas `expedientes.tests.test_documental expedientes.tests.test_concurrency`, suite general y `check`. La validación visual en SiCon real es posterior a la aplicación.
