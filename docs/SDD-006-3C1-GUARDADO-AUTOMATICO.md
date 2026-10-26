# SDD-006 · Verificación documental con guardado automático

Alcance: únicamente los 21 controles documentales existentes de la ficha del concurso.

- Al accionar un interruptor se envía un POST sin recargar si están completos los datos requeridos. Las fojas y las observaciones se envían al terminar su edición (evento `change`), no por cada pulsación.
- Activar una verificación con foja inválida o faltante no provoca una escritura; afectación presupuestaria también espera PPAL y ACTIV válidos.
- El servidor reutiliza `ControlDocumentalForm` y `actualizar_control`: permisos, CSRF, bloqueo transaccional, versión e historial permanecen vigentes.
- La respuesta JSON actualiza la versión, las fojas, el estado, el responsable, los contadores y la información de habilitación con **datos guardados**. Un conflicto `409` obliga a recargar antes de continuar.
- Sin JavaScript o `fetch` existe un botón de envío POST tradicional. No se introduce una migración ni guardado automático de etapa o estado administrativo.
- Se evitan envíos simultáneos del mismo control y se avisa al salir de la página con cambios no persistidos.

## Comprobaciones

- Sintaxis Python y JavaScript comprobada.
- Chromium sobre **formulario de prueba**, en 1280 y 360 px: guardado tras toggle, espera de fojas y códigos, contador dinámico, conflicto y visualización de error. **No equivale a QA visual de la aplicación Django real.**
- Pruebas de Django agregadas para éxito, validación, concurrencia, permisos y fallback; deben ejecutarse contra el PostgreSQL de pruebas del usuario.
- Verificar manualmente en SiCon con datos de prueba y especialmente una corrección simultánea de dos operadores. No utilizar la base real como banco de pruebas.
