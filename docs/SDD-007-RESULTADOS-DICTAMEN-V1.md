# SDD-007 · Evaluaciones y dictamen ordinario · Primera entrega

## Alcance aprobado (27/10/2026)
- Evaluación acreditada por aspirante, dos puntajes decimales y total calculado sin edición directa.
- Escala de trabajo: antecedentes **0–34**, oposición **0–51**, total **0–85**, mínimo para mérito **42,50**.
- Artículo 52 del Anexo de la Ord. 33/10-CS: desempeño laboral no computable mientras no exista evaluación.
- Artículos 6 y 41: proporción 40/60; orden descendente por total, después por oposición. Si todavía empatan, aplicar los criterios restantes del artículo 41 y **no** asignar un puesto arbitrario.
- Los puntajes de oposición se registran directamente **sobre 51**. No se convierten calificaciones sobre 60 sin respaldo documental. La equivalencia concreta 34/51 propuesta debe corroborarse con la práctica administrativa y el acta del jurado, ya que el artículo 52 por sí solo no prescribe esa operación.
- Total inferior a 42,50: listado separado, sin asignación de puesto de mérito. Todo aspirante inscripto debe contar con ambas calificaciones para habilitar el proyecto ordinario.

## Implementación
- `participantes.EvaluacionAspirante`: datos de evaluación por inscripción, no por persona global. Un puntaje cero es válido y diferente de no cargado.
- `participantes.CambioEvaluacion`: historial inmutable por edición de aplicación, motivo obligatorio para rectificaciones, responsable y fecha. Control de versión y transacción.
- Pestaña Aspirantes: formulario independiente de la inscripción y tabla de resultados / mérito. Los empates se señalan sin resolver.
- Proyecto de aprobación del dictamen: **deja de pedir líneas `puesto | ID`**, toma las evaluaciones estructuradas y genera una tabla con apellido/nombre, DNI, antecedentes, oposición, total. Registra la escala, puntajes y puesto en su instantánea; versiones DOCX históricas intactas.
- El formulario del documento exige confirmar expresamente la ausencia de recursos contra el dictamen pendientes de resolver. La confirmación no sustituye el expediente.
- La generación de designación **no se cambia** en esta fase: su modelo sigue provisional.
- Las resoluciones excepcionales y demás criterios de desempate necesitan diseño y antecedentes reales.

## Instalación
Aplicar parche sobre el ZIP SiCon-actualizado-20261027-204427; ejecutar `python manage.py migrate` por la migración `participantes.0004_evaluacion_aspirante` y luego `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test concursos participantes expedientes documentos core`.

## Casos de prueba
- 80 = 32 + 48 precede a 80 = 34 + 46.
- Total 42,50 entra; 42,49 no. Cero se registra, ausencia bloquea.
- Empate total+oposición no se resuelve por apellido, DNI ni PK.
- Rango 0–34 y 0–51; correcciones registradas, versionado concurrente.
- Denegar escritura al lector; hash de fuentes cambia al modificar resultados.
- Verificar en Docker la tabla DOCX y la migración PostgreSQL; no se ejecutaron pruebas Django en el entorno de empaquetado.
