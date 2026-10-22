# Prompt para Codex: implementar SDD-001 (copiar el texto siguiente)

Iniciemos `gestion-concursos`, sistema de gestión administrativa de Concursos Nodocentes de la UNSJ. El repositorio contiene `AGENTS.md`, especificaciones SDD, agentes revisores y skills. **No implementes todo el producto**.

1. Leé `AGENTS.md`, `docs/PRODUCTO.md`, `docs/ROADMAP-SDD.md`, `docs/DISEÑO.md`, `docs/SEGURIDAD.md`, `docs/QA.md` y `docs/specs/001-fundaciones.md`. Inspeccioná qué existe realmente en el repositorio.
2. Usá la skill `$sdd-entrega`. Aplicá `$django-calidad`, `$ui-consistente` y `$sesion-segura` cuando correspondan. Si los skills no se detectan, leé directamente sus archivos `SKILL.md` y cumplí sus procedimientos; aclaralo al entregar.
3. Mostrá un plan **breve** con entregables verificables, limitado a SDD-001. Después implementá: Django + PostgreSQL + Docker Compose; autenticación Django; login separado del layout privado; logout POST/CSRF; cierre de sesión validado en servidor por **30 minutos de inactividad humana**, no renovable por polling; UI global blanco/naranja con componentes reutilizables; panel inicial mínimo; pruebas y README con instrucciones macOS / Windows.
4. Antes del cierre, corré las pruebas y checks. Si la infraestructura o herramientas no permiten una comprobación, informá la limitación exactamente; no la simules.
5. Si están disponibles los subagentes configurados, pedí al final **revisión de solo lectura** a `revisor_django`, `auditor_ui` y `auditor_seguridad` sobre los cambios SDD-001. Respondé los hallazgos importantes y volvé a probar. Si no están disponibles, hacé la revisión equivalente con `docs/QA.md` y declaralo expresamente.
6. Informá archivos, decisiones, comandos y resultados; detallá cómo levantar y probar la app. **Detenete** al completar SDD-001.

Restricciones: no avances a SDD-002; no implementes concursos, participantes, checklist ni DOCX; no conectes CoPla; no instales frameworks nuevos sin justificación; no hagas commits, pushes, deploys ni acciones destructivas.
