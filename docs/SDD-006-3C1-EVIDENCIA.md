# SDD-006 · Fase 3C-1 · Control documental

## Alcance

- Las 21 verificaciones conservan sus cinco grupos y sus reglas actuales.
- Cada requisito presenta una fila compacta con denominación, estado explícito, foja cuando aplica, PPAL/ACTIV para afectación y aviso de observaciones.
- Se usa `<details>` nativo para editar; los formularios no se duplican ni requieren JavaScript. Un error Django deja abierto únicamente el editor afectado y conserva los datos enviados.
- Se conserva el fragmento `#documental-ID` en los POST. La fila seleccionada se destaca con `:target`; `detail-tabs.js` existente activa la pestaña propietaria del error o fragmento.
- El resumen diferencia etapa documental y estado administrativo. No cambia automáticamente etapas ni habilitaciones.
- Usuarios de solo lectura acceden a información adicional e historial sin controles de modificación.

## Archivos

`expedientes/presentation.py`, `templates/expedientes/{checklist,control_fila}.html`, `static/css/app.css` y `expedientes/tests/test_documental.py`.

## Verificación

- Compilación sintáctica Python completada.
- Pendiente de ejecutar pruebas Django/PostgreSQL y QA visual en navegador con la aplicación, pues el entorno de preparación no dispone de la dependencia Django ni de un servidor PostgreSQL conectado.
- Pruebas de regresión añadidas: 21 editores cerrados inicialmente, resumen por grupo, error que reabre editor y conserva valores, presentación de fojas/códigos/historial y permisos de solo lectura.
- Sin cambios en modelos, migraciones, servicios, sesiones, documentos DOCX ni autómatas de estados.
