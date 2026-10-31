# F4J · Panel general de gestión de concursos (30/10/2026)

## Alcance
- Sustituye la bienvenida del Panel inicial por un tablero **exclusivamente de consulta**.
- Resumen global: registrados, activos (distintos de finalizados), para revisar, con dictamen y finalizados. Los estados se toman de `Concurso.estado`, no del checklist.
- Los concursos no finalizados muestran como máximo una revisión orientativa por expediente. Orden: situación administrativa especial; acta de inscriptos verificada sin aspirantes cargados; impugnaciones vigentes; primer requisito exigible incompleto; sugerencia de estado basada en actuación completa; sugerencia de convocatoria por resolución registrada. No se infieren fechas límite ni urgencias.
- Una fila enlaza a la ficha, a la sección o al control específico. Los enlaces de cambio de estado solo se ofrecen a usuarios con el permiso vigente.
- La revisión documental reutiliza `ControlDocumental.completo` (fojas incluidas), el catálogo `REQUISITOS` y la etapa de `SeguimientoDocumental`. Las sugerencias reutilizan los servicios existentes; no hay reglas de transición nuevas.
- Sin `view_concurso`, no se hacen consultas de datos de concursos y se muestra un mensaje de acceso. Sin concursos, se muestra un estado vacío.
- Se limita la lista visible a 8 revisiones y 5 concursos sin revisión, **sin limitar los contadores globales**. El listado general existente permite consultar el conjunto.
- Se precargan controles, aspirantes y seguimiento, evitando N+1 por expediente. No hay migraciones ni operaciones de escritura.

## Verificación
```sh
python -u manage.py test core.tests.test_tablero core.tests.test_workspace -v 2
python -u manage.py test concursos participantes expedientes documentos core -v 1
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Límites conscientes
- «Para revisar» no es «vencido» ni «bloqueado»: abarca comprobaciones orientativas.
- No muestra evaluaciones pendientes ni calcula plazos por falta de una regla general aprobada para el tablero. La ficha de cada concurso conserva su análisis exhaustivo.
- Los contadores de concursos corresponden a todos los concursos visibles con `view_concurso`, no a una asignación por operador (no existe aún ese modelo de distribución).
