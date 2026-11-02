# F4M · Trazabilidad del jurado y considerandos dinámicos

**Estado:** propuesta funcional aprobada; F4M.1 aporta un motor aislado de vista previa sin integración con las vistas ni con los archivos DOCX.

## Problema

Una modificación de la integración del jurado produce dos efectos distintos:
1. Cambia quiénes integran el jurado conforme al acto administrativo aplicable.
2. Genera antecedentes que, cuando sean pertinentes, deben constar en los considerandos de las resoluciones posteriores.

No se debe equiparar la fecha en que se registró un movimiento, la fecha de emisión de la resolución y la fecha desde la cual produce efectos. Tampoco se deben interpretar los campos `fojas` como constancias verificadas automáticamente.

## Datos existentes de F4L

El modelo `ActuacionJurado` ya permite distinguir `presentacion`, `cese`, `promocion` y `designacion`; registra motivo (`excusacion` / `recusacion`), jurado, representación, calidad anterior/nueva, fecha de actuación, número de resolución, fojas, y relaciones `antecedente` / `resuelto_por`.

Para F4M.1 estos hechos se leen, **sin crear otra tabla paralela ni modificar los registros vigentes**. Un cese formal y una promoción vinculada a la misma presentación se agrupan como antecedentes de una única resolución. Una nueva designación respaldada por otra resolución produce un bloque independiente.

**Límite:** F4L no captura separadamente una fecha de efectos jurídicos ni acredita con una fecha específica el comienzo de toda designación inicial. Por lo tanto, F4M.1 **no reconstruye todavía quiénes eran los seis jurados en un día histórico concreto**; eso corresponde a F4M.2 y necesita datos explícitos y migración revisada.

## Contrato de F4M.1

La función pura `preparar_antecedentes_jurado(actuaciones, fecha_documento=None)` devuelve:
- `bloques`: número y fecha de resolución, actuaciones originales relacionadas, textos de considerandos propuestos y lista de faltantes.
- `advertencias`: presentaciones sin resolver, promociones sin cese vinculado y otras anomalías detectadas.
- `completa_para_revision`: significa *datos suficientes para revisar la propuesta*, **NO** acto emitido, fojas verificadas ni texto jurídicamente aprobado.

Si se recibe una `fecha_documento`, se incluyen únicamente resoluciones con fecha de emisión igual o anterior. Esa comparación **no equivale a afirmar que ya produjeron efectos**.

### Reglas de redacción

- Excusación: se puede afirmar que la persona indicada presentó la excusación cuando hay una presentación enlazada, y que el cese se dispuso mediante la resolución registrada.
- Recusación: F4L identifica al jurado recusado, no a quién promovió la recusación. Evitar atribuir al propio jurado la presentación.
- Promoción: no generar un segundo considerando de cese ni citar dos veces la misma resolución; aludir a la designación del suplente como titular cuando está vinculada al mismo acto.
- Nueva designación: citar a la persona, su carácter, representación, número de resolución y fojas.
- Cuando falta el número o fecha de resolución, fojas, identificación, representación, calidad o presentación de origen: **no inventar** los datos y bloquear ese bloque para incorporación a un documento.
- Una presentación pendiente **no** constituye un cese. Una promoción sin vínculo verificable no se presenta como hecho acreditado.
- Ordenar los antecedentes por fecha de emisión de los actos, con un criterio estable para empates.
- Los párrafos son borradores institucionales revisables; no representan una declaración de validez jurídica.

## Próximos incrementos

### F4M.2 · Vigencias históricas acreditadas

Registrar **fecha de inicio de efectos** o regla de efectos expresamente documentada, cuando corresponda, para cada acto de cese, promoción y designación; y definir una referencia acreditada para la integración inicial. Nunca completar fechas faltantes con `creado_en`, con la fecha del formulario o automáticamente con la fecha de resolución.

Servicio futuro: `composicion_jurado_en_fecha(concurso, fecha_documento)`, que devuelve las seis plazas o indica, con motivos, cuándo la composición histórica **no es reconstruible con certeza**. No introducir una segunda fuente de verdad contradictoria con F4L.

### F4M.3 · Interfaz de revisión

En la ficha del concurso, apartado «Antecedentes del jurado para documentos», mostrar bloques agrupados por resolución, presentación de origen, fojas, integrantes afectados, advertencias de faltantes y una vista previa editable/revisable. La edición del texto propuesto **no** cambia los hechos que originaron su redacción. Una modificación de hechos debe realizarse por el procedimiento administrativo apropiado.

### F4M.4 · Integración con generadores DOCX

Integrar sólo en los modelos que requieran antecedentes: principalmente el proyecto de resolución aprobatoria del dictamen y el proyecto de resolución de designación; verificar los requisitos particulares de cada modelo antes de insertarlos. Mantener las ocho plantillas institucionales originales y los controles de integridad; no modificar documentos históricos ni insertar automáticamente párrafos en actos previos.

La vista previa debe diferenciar «datos registrados», «respaldo documental verificado» y «texto revisado por el operador». El flujo de generación no debe convertir una revisión editorial en una verificación documental del expediente.

## Escenarios de aceptación

1. Concurso sin modificación: no producir considerandos nuevos.
2. Excusación y promoción por la misma resolución: un único bloque con presentación, acto y nueva integración.
3. Recusación: no afirmar que el jurado recusado presentó la recusación.
4. Excusación pendiente: no afirmar aceptación ni cese.
5. Fojas ausentes: no interpolar «xx» ni inventar fojas; devolver faltantes.
6. Cese y promoción no vinculados: advertir; no agrupar por mera coincidencia de número.
7. Varias resoluciones: mantener orden cronológico sin perder antecedentes.
8. Documento fechado antes de una resolución: no incluirla automáticamente en los antecedentes de ese documento.
9. Documento histórico ya emitido: no reescribirlo ni regenerarlo silenciosamente.
10. Fecha de efectos no acreditada: no informar que una integración histórica está confirmada.

## Instalación F4M.1 (Windows / PowerShell)

1. Aplicar el parche desde la raíz de SiCon.
2. Reconstruir `web` si se ejecutan las pruebas dentro de Docker, porque el servicio copia código al construir la imagen.
3. Ejecutar `docker compose exec -T web python manage.py test participantes.tests.test_jurados_considerandos -v 2`.
4. Ejecutar la suite completa antes de integrar con vistas y generadores.

**Este primer incremento no incorpora botones, formularios, migraciones, tablas nuevas ni escritura de datos.**
