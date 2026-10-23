# SDD-003 — Evidencia de implementación

**Estado:** implementación entregada; aceptación del usuario pendiente. No habilita SDD-004.

## Alcance entregado

Persona reutilizable por DNI normalizado y participaciones por concurso para jurados, veedores de APUNSJ y aspirantes. La ficha separa los tres grupos; las altas y correcciones usan formularios, permisos y componentes compartidos. La base impide duplicar una plaza de jurado o un aspirante dentro del concurso. No se cambian silenciosamente datos de una persona ya registrada.

## Verificación efectuada

| Control | Resultado |
|---|---|
| Revisión independiente inicial | `revisor_django`, `auditor_ui` y `auditor_seguridad`; los hallazgos relevantes se corrigieron y se hizo QA focal. |
| Correcciones verificadas | Versiones optimistas en edición; bloqueo y revalidación del DNI antes de reutilizar Persona; selección inicial obligatoria de representación/calidad del jurado; mensaje claro para plaza duplicada. |
| Django y PostgreSQL aislado | `manage.py check`: 0 problemas; `makemigrations --check --dry-run`: sin cambios; suite completa: **77 pruebas, OK**. `git diff --check`: sin errores. |
| Chrome aislado con datos sintéticos | Revisados 1440, 1280, 768 y 360 px: secciones vacías y pobladas, tres flujos de alta, foco por teclado, selección obligatoria y desplazamiento de tablas angostas; sin desbordamiento horizontal de página. |

**Límite de verificación visual:** la llamada a `showPicker()` devolvió éxito, pero la captura headless no mostró el menú nativo abierto. La inspección visual de ese popup queda pendiente; no se declara comprobada.

## Límites y siguiente paso

No se aplicó la migración a la base persistente. No hubo commit, push ni despliegue. No se implementaron reasignación o desactivación de personas, sustituciones e historial de reemplazos, fotografía histórica definitiva, SDD-004/005 ni integración CoPla. La expresión «DNI duplicado/localidad» de la especificación no define una regla de localidad; no se agregó ninguna. Corresponde la revisión y aceptación expresa del usuario antes de avanzar de fase.
