# Modelos DOCX aportados el 30/10/2026

Se utilizan como archivos Word originales (no una reconstrucción manual):
- `Acta de sorteo de temas.docx`, ahora tipo `sorteo_acta`.
- `PROYECTO RES. APROBANDO DICTAMEN.docx`, reemplaza el borrador programático anterior.
- `PROYECTO RES. DESIGNACION.docx`, reemplaza el borrador programático anterior.

## Límites y hechos que requieren intervención expresa

- Los textos fijos de los modelos se conservan. Los datos de un concurso particular
  (personas, cargos, fecha y hora, sobres, tema sorteado, resoluciones, fojas y presupuesto)
  se reemplazan con fuentes estructuradas o declaraciones expresas del operador.
- El acta contiene un listado variable de jurados y aspirantes presentes y situación del
  veedor gremial; los ausentes no se declaran notificados ni se agregan a la firma.
- Las dos resoluciones mantienen las afirmaciones literales del modelo sobre unanimidad,
  ausencia de impugnaciones, notificación en plazo, autoridad que suscribió el acta y
  comunicación del tema; se requiere que el operador confirme los hechos. Una afirmación
  distinta exige revisión institucional de otro modelo, no generación por omisión.
- El modelo de designación describe específicamente una vacancia causada por jubilación.
  Si la causa es distinta, **no se genera** con este DOCX para no afirmar una jubilación
  inexistente. La limitación de un cargo anterior es opcional y, de corresponder, se
  exige identificar sus datos en vez de copiar los de un ejemplo.
- Se preservan los DOCX históricos ya generados en la base. Se versiona cada plantilla y
  se incluye el hash del archivo fuente en la instantánea de la generación.
- Generar un DOCX no verifica actuaciones ni emite, firma, notifica o designa.
- No se agregó migración.

## Verificación pendiente

Se pudieron abrir y renderizar muestras de los tres archivos fuente con los marcadores
resueltos. La suite Django/PostgreSQL debe ejecutarse en la instalación del usuario.
