# SDD-006 · Fase 3C-2 · Generación documental

**Alcance:** presentación de la sección «Documentos» y de la pantalla «Revisar borrador». Sin cambios en modelos, migraciones, plantillas DOCX, permisos, validaciones, snapshots ni descargas.

## Cambios

- Los siete tipos existentes aparecen agrupados por momento del trámite, sin modificar el orden ni el catálogo de `documentos/registry.py`.
- Estado de datos disponibles, faltantes expandibles y enlace de revisión para operadores autorizados. **Datos disponibles** no implica aprobación institucional del modelo ni emisión del acto.
- Señales explícitas para APUNSJ y oficio al Rector (modelos provisorios), así como proyectos de dictamen y designación todavía pendientes de consolidación.
- Generaciones históricas: lectura compacta de tipo, fecha, autor, versión, descarga principal y notas individuales bajo un detalle desplegable. Conserva límite de últimas veinte generaciones y reglas de acceso.
- Revisión: disponibilidad y faltantes primero, fuentes y datos automáticos consultables sin despliegue inicial excesivo. Complementos ordenados y 21 campos de presupuesto de designación dentro de un bloque desplegable; si tienen errores de campo, se abre automáticamente.
- Se reutilizan `components/button.html`, los campos Django originales y el CSS compartido.

## Integridad y regresiones

- Sin cambios en `services.generar`, `preparar_revision`, modelos DOCX, validadores, transacciones, descargas o historial de generaciones.
- Se conserva el formulario POST, CSRF, huella y versiones de concurrencia. Los campos de presupuesto se envían igual aunque el detalle esté cerrado; nunca se deshabilitan.
- No se agregan dependencias JS ni se requiere JavaScript para consultar requisitos.
- Se agrega `documentos/test_ui.py` para comprobar siete tipos, agrupación, permisos y unicidad de campos de revisión.

## Verificación local del artefacto

- Compilación de sintaxis Python de los archivos modificados: correcta.
- `git diff --check`: sin errores de whitespace.
- Aplicación del parche sobre la base de código recibida tras 3C-1: por verificar con `git apply --check` antes de la entrega.
- **Django/PostgreSQL y QA visual en navegador:** pendientes de ejecutar en la instalación del proyecto; no se declaran pruebas completas ni QA visual aprobados.

## Aceptación sugerida

1. Abrir ficha de un concurso, pestaña «Documentos», en escritorio y móvil. Ver las tres agrupaciones y los siete tipos.
2. Abrir detalle de faltantes en un documento no disponible. Seguir el enlace de revisión y comprobar que el bloqueo sea claro y no permita generar.
3. Abrir proyecto de convocatoria y luego designación. Revisar ubicación de campos (incluidos 21 presupuestarios), errores y envío.
4. Generar o descargar un documento de prueba; confirmar que la descarga histórica y, para jurados, las seis notas individuales continúen funcionando.
5. Acceder como usuario de solo lectura y comprobar que no haya acciones de generación.
