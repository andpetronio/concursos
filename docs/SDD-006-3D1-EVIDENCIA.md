# SDD-006 · Fase 3D-1: Refinamiento visual focalizado

**Alcance:** ajustes únicamente en `static/css/app.css`, sobre el estado acumulado de SDD-006 (3B, 3C-1, 3C-2 y guardado automático). No es el cierre del refinamiento transversal completo.

## Intervenciones

- **Control documental:** mayor separación visual entre las cinco secciones, cabeceras de etapa y contadores definidos; filas con mejor ritmo de lectura; panel de fojas/PPAL/ACTIV distinguible cuando se abre; metadatos e historial secundarios; foco visible y hover discreto.
- **Generación documental:** mejor diferenciación entre grupos y filas, botones de revisión conservados, y mayor separación en el historial.
- **Participantes:** acciones de editar participación y corregir persona visualmente diferenciadas, sin modificar etiquetas ni destinos.
- **Ficha y configuración:** barra de pestañas con separación visual sutil y estados de foco en las tarjetas institucionales.
- Respeta `prefers-reduced-motion` en las transiciones afectadas.

## Riesgo y compatibilidad

- Sin cambios en modelos, migraciones, servicios, templates, JavaScript, permisos o guardado automático.
- Se mantienen las alturas de los controles de 44 px, la visibilidad de fojas, las etiquetas y las variantes de estado existentes.
- **Validación técnica local:** `git diff --check`; análisis sintáctico de CSS con `tinycss2`; prueba visual de componentes sintéticos en Chromium a 1280 y 360 px, sin desborde horizontal ni errores de consola.
- **Pendiente en instalación de SiCon:** ejecutar las pruebas Django habituales y revisar en una ficha real con los cinco grupos y las pestañas existentes. La prueba visual sintética no es una validación de integración con Django.

## Siguientes trabajos

- Completar 3D con una pasada visual de formularios, listados, configuración, login/dashboard e historiales sobre capturas reales.
- Fase 4: diseñar y aprobar explícitamente el avance automático de la **etapa documental** Preparación → Convocatoria cuando se cumplan los cinco requisitos previos. El **estado administrativo** Convocado sigue separado de ese avance.
