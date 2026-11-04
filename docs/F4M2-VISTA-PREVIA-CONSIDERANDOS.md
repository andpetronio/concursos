# F4M.2 · Vista previa de antecedentes y considerandos del jurado

## Alcance entregado

La ficha del concurso incorpora, en **Jurados**, el enlace **Revisar antecedentes y considerandos**. Se abre una pantalla protegida por el permiso `concursos.view_concurso`, con:

- Filtro opcional de fecha del documento, aplicado a la **fecha de emisión de las resoluciones** registradas.
- Bloques de considerandos agrupados por cese y eventual promoción formal bajo el mismo acto; nuevas designaciones en bloques independientes.
- Advertencias por presentaciones sin resolver y promociones sin cese vinculable.
- Faltantes expresos para resoluciones sin fojas, fecha o datos suficientes. Los bloques incompletos no muestran un texto generado.
- Aviso de que los textos son borradores revisables, no constancias de verificación documental ni resoluciones emitidas.

## Fuente de información

`participantes.jurados_considerandos.preparar_antecedentes_jurado` (F4M.1) lee exclusivamente `ActuacionJurado` (F4L); la nueva vista no crea ni modifica registros.

## Límites de este incremento

- **No** reconstruye la vigencia de cada plaza en una fecha histórica: falta registrar separadamente la fecha de efectos administrativos.
- **No** verifica que las fojas registradas obren materialmente en el expediente.
- **No** incorpora los párrafos a los proyectos DOCX ni cambia las plantillas existentes.
- **No** edita los considerandos, ni los considera aprobados.
- Si se carga una fecha inválida, no se muestran resultados sin aplicar el filtro.

## Instalación y pruebas en Mac

El parche `SiCon-F4M2-vista-previa-considerandos-mac-zsh.patch` requiere F4L y F4M.1 en el árbol de trabajo. El paquete ZIP incluye F4M.1 por si todavía no llegó al repositorio de la Mac.

```zsh
# Desde la raíz del proyecto y con los cambios locales controlados:
git apply --check "$HOME/Downloads/SiCon-F4M2-vista-previa-considerandos-mac-zsh.patch"
git apply "$HOME/Downloads/SiCon-F4M2-vista-previa-considerandos-mac-zsh.patch"
docker compose up -d --build web
docker compose exec -T web python manage.py test \
  participantes.tests.test_jurados_considerandos \
  participantes.tests.test_jurados_considerandos_ui -v 2
```

No requiere migraciones. Los modelos de generación DOCX permanecen intactos.
