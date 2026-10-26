# SDD-006 · Fase 4B · Sugerencia de estado Convocado

## Alcance

Cuando un concurso se encuentra administrativamente en **Preparación** y tiene registrado el número de **resolución oficial de convocatoria**, su ficha ofrece revisar el cambio a **Convocado**. No modifica el estado al registrar el número ni al abrir el enlace.

- El enlace conduce al formulario de cambio de estado, precargado con «Convocado» y una justificación editable que refiere al número registrado.
- Solo usuarios con `concursos.cambiar_estado_concurso` pueden confirmar la modificación. Los usuarios de consulta ven una orientación, pero no el enlace para cambiar estado.
- Guardar continúa usando el servicio vigente, su `version_esperada`, sus permisos y su historial; no se agrega ningún endpoint, migración, tarea automática o inferencia de firma/emisión por generación DOCX.
- No se ofrece la sugerencia si falta el número oficial o si el estado dejó de ser Preparación. La lógica de sugerencia «Con dictamen» sigue independiente.

## Alcance no modificado

El avance automático de la **etapa documental** Preparación → Convocatoria implementado en 4A es distinto de esta sugerencia del **estado administrativo**. No se exige checklist completo para presentar una sugerencia basada en el número oficial. La decisión definitiva siempre corresponde a la autoridad operativa con permiso.

## Verificación

Se agregan pruebas para la condición de sugerencia, ausencia de efectos en GET, precarga del formulario, confirmación y bitácora, desaparición luego del cambio y restricciones de permisos. Ejecutar la suite en Django/PostgreSQL y revisar visualmente la ficha y el formulario.
