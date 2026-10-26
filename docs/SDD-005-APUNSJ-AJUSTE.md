# SDD-005 · Oficio APUNSJ y retiro de oficio al Rector

- Referencia aportada: `documentos/modelos/solicitar veedor.docx`.
- `apunsj-3`: redacción administrativa actualizada (cinco párrafos) suministrada para el oficio de solicitud de veedor, conservando literalmente la formulación y sustituyendo únicamente los datos propios de cada concurso. Datos variables desde el concurso, resolución oficial desde la ficha y destinatario institucional versionado; fecha de preparación automática; membrete vigente de Configuración institucional. El documento no incorpora firma ni presume su emisión.
- Requiere resolución oficial, destinatario configurado y membrete. La revisión excepcional de modalidad Acotado ya no se exige para este oficio, puesto que el modelo aportado contempla esa modalidad.
- Se retira la generación del oficio al Rector (`solicitud_jurados_rectorado`), pero **no** se eliminan documentos antiguos: siguen accesibles por las rutas históricas y los controles de integridad.
- Se conserva íntegro el requisito documental de indicación de jurados por el Rectorado (`jurado_rectorado`), con fojas, verificación e historial.
- No hay cambios de modelo, migraciones, catálogo documental del expediente ni verificaciones automáticas.
- Validación pendiente en entorno Django/PostgreSQL real y revisión visual del DOCX con membrete institucional vigente.

- La revisión de texto `apunsj-3` no altera generaciones previas `apunsj-2`: cada archivo conserva sus bytes, su versión y su instantánea.
