# Uso de agentes y skills en Codex

## Diferencia
- **Agente**: subagente con un rol específico de revisión; configuración TOML en `.codex/agents/`. El agente principal implementa y coordina; revisores **no editan** por instrucción, pero **heredan permisos**, así que la instrucción no equivale a un sandbox de solo lectura.
- **Skill**: instrucciones procedimentales bajo `.agents/skills/<nombre>/SKILL.md`, disponibles según el trabajo o por invocación explícita `$nombre`.

## Agentes configurados
| Agente | Cuándo | Mandato | Producto esperado |
|---|---|---|---|
| `revisor_django` | Fin de cada fase backend y ante cambios estructurales | ORM, arquitectura, duplicación, migraciones, tests | Hallazgos priorizados con rutas, líneas y pruebas |
| `auditor_ui` | Fases con pantallas y cambios de diseño | Tokens, componentes, responsive, accesibilidad | Hallazgos concretos y evidencia visual si existe |
| `auditor_seguridad` | SDD-001 y fases con autenticación, permisos o datos de personas | Sesiones, CSRF, controles de acceso y privacidad | Vulnerabilidades demostrables y pruebas faltantes |

Los tres pueden revisar **en paralelo al finalizar SDD-001**, cuando Codex lo soporte y el costo esté justificado. No convocarlos durante cada cambio trivial. El agente principal es el único responsable de integrar las correcciones. Se prohíbe atribuir a un agente una revisión no ejecutada.

## Skills configuradas
| Skill | Disparador |
|---|---|
| `$sdd-entrega` | Inicio y cierre de cualquier fase especificada |
| `$django-calidad` | Modelos, vistas, forms, DB, tests y migrations |
| `$ui-consistente` | Toda creación/cambio de templates, CSS, UI o JS visual |
| `$sesion-segura` | Autenticación, sesión, actividad y cierre de sesión |
| `$documentos-docx` | Solamente cuando se autorice la generación documental |

## Protocolo de revisión
1. El agente principal implementa la especificación y ejecuta pruebas locales.
2. Pide a revisores independientes que observen **el diff**, la especificación y sus criterios de aceptación; respuestas de lectura, sin modificaciones.
3. Prioriza fallos reproducibles, seguridad, integridad y pruebas faltantes por encima de opiniones estilísticas no vinculadas al sistema de diseño.
4. Corrige y vuelve a ejecutar los checks; documenta bloqueos reales.
5. Entrega el resultado y se detiene. **No se delega la aprobación humana del avance.**

## Compatibilidad
Config de proyecto en `.codex/config.toml`; los agentes especializados en `.codex/agents/*.toml`; skills en `.agents/skills/*/SKILL.md`. No se fijan modelos en los agentes, para respetar la configuración disponible. Si la versión instalada no soporta subagentes, usar el control humano y checklist de `docs/QA.md` como alternativa explícita.
