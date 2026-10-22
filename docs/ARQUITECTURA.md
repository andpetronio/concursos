# Arquitectura técnica aprobada (sin sobreingeniería)

## Stack
- Backend: Django + Python estable y compatible; versiones concretas a fijar razonadamente al iniciar SDD-001.
- DB: PostgreSQL con volumen persistente en Docker Compose.
- UI: Django Templates + CSS centralizado + JavaScript progresivo solo donde corresponda.
- Autenticación/sesiones: mecanismos nativos de Django más componente acotado para inactividad real.
- Documentos (fase posterior): generación de `.docx` editables desde plantillas verificadas.

## Estructura deseada: conceptual, no crear módulos vacíos
- `config/`: settings, URLs, ASGI/WSGI según necesidad.
- `core/`: autenticación, layout y piezas compartidas.
- `concursos/`: concurso, estados e historial (SDD-002).
- `participantes/`: personas, jurados, veedores, aspirantes (SDD-003).
- `expedientes/`: checklist, fojas y actuaciones (SDD-004).
- `documentos/`: plantillas, generación y registro (SDD-005).
- `templates/` y `static/`: recursos reutilizables.
- `tests/` o pruebas por app: seguir una sola convención coherente.

**Crear cada app cuando su fase lo requiera**, no todo el árbol vacío por adelantado. `core` puede ser una app o un módulo según simplifique el proyecto.

## Reglas de diseño
1. Django Forms valida inputs; modelos contienen invariantes persistentes; views coordinan; servicios únicamente para operaciones que justifiquen extracción.
2. Evitar signals para efectos de negocio poco transparentes; preferir llamadas explícitas para sugerencias de estado, generación de DOCX y futura integración.
3. Toda edición relevante usa ORM, migraciones y validaciones; no SQL ad-hoc sin necesidad.
4. Las fojas son cadenas validadas (`5`, `5/8`) que preservan la notación administrativa. No deducir numeración ni foliar expedientes digitalmente.
5. Personas se identifican por DNI normalizado, y las relaciones a concursos no deben duplicar personas. La necesidad de conservar datos históricos en actos se evalúa antes de SDD-003/005.
6. Roles de edición y estados no se inventan: permisos mínimos en SDD-001, ampliar solo cuando haya definición.
7. Historial de cambios de estado auditable; no mutar antecedentes históricos silenciosamente.
8. La integración con CoPla será por interfaz/API autorizada; la base de CoPla permanece independiente.

## Seguridad y operación
Ver `docs/SEGURIDAD.md`. No incorporar a Git `.env`, datos personales reales ni dumps. Docker Compose para desarrollo local, con comandos documentados para macOS y Windows + Docker Desktop.
