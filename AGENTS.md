# AGENTS.md — Sistema de Gestión de Concursos Nodocentes (UNSJ)

## Misión y alcance
Desarrollar un sistema administrativo para la **Dirección de Concursos Nodocentes** de la Universidad Nacional de San Juan. Se registran concursos, jurados, veedores, aspirantes, controles documentales y documentos DOCX editables. El expediente y los actos administrativos oficiales **no** son reemplazados por la aplicación.

## Orden de lectura para toda tarea
1. Este `AGENTS.md`.
2. `docs/PRODUCTO.md`, `docs/DECISIONES.md` y `docs/ROADMAP-SDD.md`.
3. **Solo** la especificación `docs/specs/NNN-*.md` aprobada para la tarea.
4. Las guías de `docs/ARQUITECTURA.md`, `docs/DISEÑO.md`, `docs/SEGURIDAD.md` y `docs/QA.md` en cuanto correspondan.
5. Código, pruebas y patrones reales existentes en el repositorio.

Prevalece el alcance explícito de la especificación vigente. Las ambigüedades de negocio no se resuelven por intuición; documentar el asunto en `docs/DECISIONES.md` solo si es material y evitar fijar reglas que no fueron aprobadas. No convertir referencias normativas en automatismos no acordados.

## Principios críticos e innegociables
- **Consistencia visual (CRÍTICA)**: `docs/DISEÑO.md` es la única fuente de tokens/componentes. Fondo `#FFFFFF`, superficies `#F8FAFC`, navegación `#FFFFFF`, naranja `#C65A17`, texto `#263342`, bordes `#E2E8F0`. El login tiene layout propio, pero conserva la identidad.
- **Reutilización / Django idiomático (CRÍTICA)**: Django ORM, Forms, Auth, Sessions, migraciones, CSRF, vistas y permisos nativos. Una sola implementación de cada componente visual o regla compartida. No duplicar validaciones entre vistas, formularios y servicios sin motivo.
- **Seguridad (CRÍTICA)**: 30 minutos **reales** sin actividad del usuario; expiración controlada en servidor, sin prolongación por polling, peticiones automáticas o pestañas inactivas. Logout mediante POST/CSRF. Ninguna operación protegida después de expirar. Más detalles en `docs/SEGURIDAD.md`.
- **Trazabilidad**: distinguir proyecto DOCX, resolución oficial y check de incorporación al expediente. Preservar historial de cambios de estado y referencias de fojas. Registrar quién/cuándo para cambios relevantes.
- **Criterios de calidad**: pruebas relevantes, chequeo de migraciones, manejo de errores, accesibilidad básica, cambios acotados. No declarar «probado» sin evidencia.

## Stack y límites
- Python + Django, PostgreSQL, Docker Compose; HTML con Django Templates, CSS compartido y JavaScript progresivo. Sin SPA, React, microservicios o complejidad especulativa.
- Repositorio nuevo, **independiente de CoPla**. Integraciones futuras por API, no lectura directa de su base ni duplicación de reglas de ATF, designaciones o vacancias.
- Usar español argentino en UI y documentación. Nombres técnicos coherentes. Evitar lenguaje inclusivo con «x/e».
- Mantener secretos en variables de entorno, no en Git. No registrar DNI, teléfonos, emails, cookies ni tokens en logs innecesarios.
- Nunca agregar `.env` real, datos reales, respaldos o documentos con información privada al repositorio.

## Método SDD: una fase por pedido
1. Inspeccionar el repositorio y leer la especificación seleccionada.
2. Resumir en pocas líneas plan, alcance, pruebas y riesgos. No crear documentos ceremoniales.
3. Implementar solamente lo autorizado. Preferir soluciones pequeñas y legibles.
4. Ejecutar checks/pruebas y comprobar UI real cuando exista un navegador disponible. Si no hay navegador, informar claramente qué no se verificó.
5. Solicitar **revisión independiente** de agentes especializados **cuando estén disponibles**, según `docs/AGENTES-Y-SKILLS.md`. Las observaciones reales deben resolverse o quedar justificadas.
6. Informar archivos modificados, comandos corridos, resultados y pendientes. **Detenerse al cerrar la fase**.

No hacer commit, push, deploy, borrar datos persistentes, alterar CoPla o ampliar el alcance sin autorización expresa.

## Agentes y skills del repositorio
- Definiciones: `.codex/agents/` (agentes revisores de solo lectura por instrucción; NO tienen sandbox independiente).
- Skills: `.agents/skills/` (guías específicas con `SKILL.md` y metadatos).
- Usar `$sdd-entrega` al iniciar/cerrar cada especificación; `$django-calidad` al intervenir backend o base de datos; `$ui-consistente` para cada UI; `$sesion-segura` en autenticación/sesión; `$documentos-docx` solo en fase documental.
- Para SDD-001 pedir revisión al `revisor_django`, `auditor_ui` y `auditor_seguridad` al terminar, si Codex admite subagentes. **No fingir** revisiones si no están disponibles; ejecutar la lista manual de `docs/QA.md`.
