# Criterios de calidad y evidencia

## Definition of Done por fase
- [ ] Alcance de la especificación vigente satisfecho, sin funcionalidades adelantadas.
- [ ] Estilo y componentes consistentes con `docs/DISEÑO.md`.
- [ ] Validaciones correctas y mensajes comprensibles (incluye error y estado vacío).
- [ ] Sin lógica duplicada ni abstracciones innecesarias.
- [ ] Autenticación/permisos correctos en todas las operaciones nuevas.
- [ ] Migraciones reproducibles y sin pendientes inesperados.
- [ ] Pruebas automatizadas para caminos normales, errores, límites e invariantes relevantes.
- [ ] `manage.py check` y suite apropiada ejecutados; resultados reportados literalmente.
- [ ] Si hay UI y navegador disponible: verificación visual responsive/foco/contraste. Si no, anotada como pendiente, nunca fingida.
- [ ] Revisiones de subagentes relevantes realizadas o reemplazadas por checklist manual explícito.
- [ ] README actualizado con comandos reales y límites conocidos.
- [ ] Sin secretos, PII de prueba real, dumps o cambios en CoPla.

## Evidencia de entrega
Reportar comandos ejecutados con salida resumida, cobertura concreta de pruebas, archivos modificados, decisiones técnicas significativas, y problemas abiertos. No decir «todo OK» si falta una comprobación.

## Revisión independiente
`revisor_django`: bugs o acoplamiento, migraciones, validación, N+1, test gaps. `auditor_ui`: estilos compartidos, layout, estados y accesibilidad. `auditor_seguridad`: servidor valida sesión, CSRF, permisos y minimización de PII. Cada hallazgo debe indicar **impacto + reproducción + localización**. Prioridad alta a los defectos reales; no inflar sugerencias cosméticas.
