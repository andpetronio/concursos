# SDD-006 · Ficha y participantes — corrección 3A

**Estado actual (25/10/2026): corrección por pestañas implementada, NO aceptada; requiere aceptación visual y funcional del usuario.** Ver §7. Las secciones 1–6 conservan la evidencia histórica de la primera entrega, reemplazada parcialmente por esta corrección.

Ficha productiva rediseñada; **pendiente de aceptación visual y funcional del usuario**. Sin fase 3B, máscaras, cambios de negocio ni propagación a otras pantallas. Capturas de aplicación Django real con datos exclusivamente **sintéticos**.

## 1. Archivos modificados
- `templates/concursos/detalle.html` y `templates/participantes/{jurados_tabla,veedores_tabla,aspirantes_tabla}.html`.
- Nuevos parciales mínimos: `templates/participantes/acciones.html`, `templates/components/table_scroll_help.html`.
- `static/css/app.css`, `core/tests/test_detail_presentation.py`, breve patrón en `DISEÑO.md`, esta evidencia y `evidencias/sdd-006/3a/`.
- Baseline por SHA-256: `/tmp/sicon-3a-qa/baseline.json`; comparación final: `changed-files.json` en esa misma carpeta temporal. Cambios anteriores preservados; sin modificaciones de vistas, forms, modelos, migraciones, servicios, URLs, configuración, tokens, sesión ni navegación 2A. Sin commit, push o deploy.

## 2. Componentes reutilizados
`layouts/private`, `table` (región etiquetada y enfocable, caption), `button`, `status`, `form_section_header`, estados vacíos y paginación; identidad `person_identity` de 2B. Checklist, controles, generación e historial conservan sus parciales reales. Se mantienen las tres interfaces de tabla y la columna Unidad; solo acciones y ayuda se comparten, sin tabla universal condicional ni biblioteca nueva.

## 3. Decisiones visuales
- Cargo como H 1; expediente inmediatamente debajo. Modalidad/categoría/tramo/agrupamiento separados de estado administrativo, situación y etapa documental. Datos completos abiertos; dos pares etiqueta/valor por fila en escritorio amplio.
- Índice HTML a resumen, datos, jurados, veedores, aspirantes, control, documentos e historial. IDs anteriores, acciones POST documentales y paginación preservados; sin pestañas ni JavaScript adicional.
- Apellido/nombre fuertes; DNI siempre visible para homónimos. Título, unidad, cargo histórico, representación/calidad, inscripción y contacto íntegros, en segundo nivel legible.
- Editar vínculo y Corregir persona diferenciados; fila horizontal en escritorio, acomodación dentro de columna hasta 760px. Objetivos≥44px. Tablas con scroll propio, ayuda visible y acceso por Tab/flechas; no se cambia `.table-actions` del piloto.

## 4. Capturas reales
PNG inspeccionados visualmente. Los nombres identifican pruebas, no registros operativos. Total 23 capturas, aproximadamente 2,8 MB; no contienen cookies ni tokens visibles.

| Vista | 1440px | 1280px | 768px | 360px |
|---|---|---|---|---|
| Ficha | [Ver](evidencias/sdd-006/3a/prueba-sintetica-ficha-1440.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-ficha-1280.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-ficha-768.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-ficha-360.png) |
| Jurados | [Ver](evidencias/sdd-006/3a/prueba-sintetica-jurados-1440.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-jurados-1280.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-jurados-768.png) | [Identidad](evidencias/sdd-006/3a/prueba-sintetica-jurados-360.png) · [Acciones](evidencias/sdd-006/3a/prueba-sintetica-jurados-acciones-360.png) |
| Veedores | [Ver](evidencias/sdd-006/3a/prueba-sintetica-veedores-1440.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-veedores-1280.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-veedores-768.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-veedores-360.png) |
| Aspirantes | [Ver](evidencias/sdd-006/3a/prueba-sintetica-aspirantes-1440.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-aspirantes-1280.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-aspirantes-768.png) | [Ver](evidencias/sdd-006/3a/prueba-sintetica-aspirantes-360.png) |

Preservación: control [1280](evidencias/sdd-006/3a/prueba-sintetica-control-documental-1280.png)/[360](evidencias/sdd-006/3a/prueba-sintetica-control-documental-360.png); documentos e historial [1280](evidencias/sdd-006/3a/prueba-sintetica-documentos-1280.png)/[360](evidencias/sdd-006/3a/prueba-sintetica-documentos-360.png); [vacío 1280](evidencias/sdd-006/3a/prueba-sintetica-ficha-vacia-1280.png) y [lector 360](evidencias/sdd-006/3a/prueba-sintetica-lector-aspirantes-360.png).

## 5. Pruebas y resultados
- RED:6 regresiones nuevas,4 fallos esperados de estructura/identidad/anclas antes de implementar. GREEN final: **check sin observaciones;134 pruebas OK,15,327s**, TEST destruida.

```sh
docker compose run --rm --no-deps -v "$PWD:/app:ro" web sh -c 'python manage.py check && python manage.py test core.tests.test_detail_presentation core.tests.test_auth core.tests.test_concurrency core.tests.test_navigation core.tests.test_workspace concursos.tests.test_concursos participantes.tests.test_participantes participantes.tests.test_ajustes expedientes.tests.test_documental --noinput'
node /tmp/sicon-3a-qa/browser.js http://127.0.0.1:9237 http://127.0.0.1:8787 /tmp/sicon-3a-qa
```

- QA:WSGI Django+static, código `/app:ro`, **URLconf productivo sin ruta piloto**, DB exclusiva `test_sicon_3a_qa` creada/destruida con runner y rechazo de TEST preexistente. Chrome headless propio, perfil `/tmp/sicon-3a-chrome-qa`, CDP 9237; sin perfil/pestañas del usuario, intercepción ni autenticación simulada. Scripts/logs/métricas en `/tmp/sicon-3a-qa/`, no en Git.
- HTTP/CSRF/cookies reales: loginPOST 302, fichaGET 200; GET/POST de edición de jurado, veedor, aspirante y corrección de persona, POST 302 y refresh con datos persistidos. Nombres similares diferenciados por DNI/inscripción; observación original y fojas `5/8` preservadas al reenvío real del control. Etapa y control vuelven respectivamente a `#control-documental` y `#documental-…`. **Participantes ya retornaban sin fragmento**: se comprueba ese contrato, no se les atribuye retorno a ancla.
- Cuatro anchos,17 mediciones: sin overflow horizontal global, acciones≥44px, horizontales en escritorio; índice con 8 destinos válidos, foco en secciones nuevas, Tab y flechas reales en tablas. Menú 2A:visible solo≤760, abrir/Escape/retorno de foco e `inert` correctos. Lector sin acciones/formularios de escritura, POST real con CSRF rechazado 403.
- Se corrigió un recorte local de 5,4px en acciones mediante ancho intrínseco `max-content`; viewport 1440 estable demostrado antes/después del foco. Se pausó y obtuvo auditoría fresca de aislamiento antes de continuar. La medición 756 posterior al fallo correspondía a liberación de emulación al cerrar CDP, **no** a un resize de la app probado. Registros `focus-*.json` conservan métricas en la misma sesión. Cero excepciones JS; se distingue faviconGET 404 preexistente y posibles 429 del limitador de actividad de errores funcionales.
- Chrome cerrado mediante `Browser.close`; servidor propio detenido y `cleanup.txt` confirma TEST destruida; sin listeners8787/9237. `node core/tests/navigation.test.js`:OK (DOM simulado, complementario al navegador real).
- `git diff --check`:sin errores. No se reejecutó `makemigrations`:no cambian modelos/migraciones; permanece el pendiente preexistente `documentos.DestinatarioPersonal.id` (exit 1 en 2B), sin corregirlo ni declarar verde ese chequeo.

## 6. Limitaciones y pendientes
- Al tabular, Chrome puede dejar inicialmente parte de un enlace fuera de la región estrecha (observado en veedores 768). **No se promete autopan completo**:región enfocada+flechas permite mostrar íntegra cada acción, Tab permite enfocarla; comprobado con teclado y sin desplazar horizontalmente la página. No se añade JS productivo para forzarlo.
- Primera entrega 3A, no aceptación de toda 2B/piloto, de DOCX o de hallazgos H 10. No recertifica 52 rutas, otras pantallas ni todos los estados documentales. Generaciones vacías en la fixture; la lógica y parciales de borradores se conservan sin auditarlos nuevamente.
- Revisión independiente focalizada realizada, sin hallazgos confirmados; inspeccionó las 23 capturas y los registros de pruebas, permisos, persistencia y teclado. Verificó la preservación textual contra el baseline SHA-256: tablas desde HEAD y detalle reconstruido determinísticamente en memoria con hash idéntico, sin presentarlo como copia original conservada. El agente principal inspeccionó además cabeceras en los cuatro anchos y acciones de jurados en escritorio/móvil. No se recertificaron errores, controles deshabilitados ni apertura nativa de selects.
- Pendiente aceptación explícita visual y funcional del usuario. **Detenerse aquí; no 3B.**


## 7. Corrección 3A: pestañas y acciones (25/10/2026)

**Alcance cerrado en implementación, pendiente de aceptación. No 3B/3C.** La petición expresa reemplaza el índice de anclas de la primera entrega por ocho pestañas, sin cambiar reglas administrativas.

### Cambios y decisiones reutilizables
- Ficha: ocho paneles, con sus secciones/IDs originales intactos. Con JavaScript solo se muestra el seleccionado; sin JS, si falta el recurso o si falla la inicialización, permanecen accesibles los ocho y sus enlaces. Sin clonado de DOM, AJAX, storage ni librerías.
- Barra sticky compacta; scroll horizontal local e indicación textual de opciones fuera de vista. ARIA progresivo (`tablist/tab/tabpanel`), selección con subrayado y peso; activación manual: flechas/Home/End recorren, Enter/Espacio activan, Tab sale al panel/controles.
- Hash original → panel propietario mediante DOM, incluidos `#documental-ID`. Refresco/atrás/adelante y enlaces internos conservan selección y querystring; errores Django tienen prioridad inicial y no se recrean ni vacían formularios. Paginación de Historial incorpora su fragmento también sin JS.
- Éxitos de alta/edición de participantes devuelven su fragmento canónico. Corrección de persona recibe una sección de una lista cerrada, comprobada contra la participación de esa persona en el concurso; no admite URL de retorno abierta. Es el único cambio de vista, exclusivamente de navegación.
- Acciones de las tres tablas reutilizan `button`: edición de participación/inscripción y corrección de persona con etiqueta explícita y borde discontinuo, en una fila en escritorio y acomodación en móvil; objetivos ≥44px. Permisos y destinos de operaciones conservados.
- Checklist de 21 controles y sección de documentos se incluyen íntegros desde los mismos parciales; no se rediseñaron formularios ni se modificaron servicios, modelos, migraciones, validaciones, DOCX, sesión o menú 2A.

### Archivos de esta corrección
- `templates/concursos/detalle.html`; nuevo `static/js/detail-tabs.js`; reglas acotadas de componentes en `static/css/app.css`.
- `templates/participantes/acciones.html` y las tres tablas; `participantes/views.py` (solo fragmento de éxito); `templates/components/pagination.html` (fragmento opcional, sin alterar consumidores que no lo pasan).
- `core/tests/test_detail_presentation.py`, nuevo `core/tests/detail_tabs.browser.test.js`; actualización de una expectativa de redirección en `participantes/tests/test_participantes.py`.
- Patrón breve en `docs/DISEÑO.md`, esta evidencia y `docs/evidencias/sdd-006/3a/correccion-tabs/`. Copias originales exactas y SHA-256 antes de editar: `/tmp/sicon-3a-tabs-qa/baseline/` y `baseline.json`; comparación en `changed-files.json`. No se descartaron cambios anteriores.

### QA y resultados
- **Django check sin observaciones; 139 pruebas OK (15,390s)**. Cinco regresiones adicionales a las 134 anteriores: paneles progresivos, POST directo a participantes, retorno de persona seguro, error documental con valores conservados y paginación con query/fragmento. TEST de suite destruida. `node core/tests/navigation.test.js`: OK (DOM simulado, complementario). Sintaxis JS y `git diff --check`: OK.
- **Chrome real, HTTP Django y URLconf productivo**, con login, cookies y CSRF reales. BD exclusiva `test_sicon_3a_tabs_qa`, rechazo si preexistía, creada y destruida con runner. Contenedor temporal `--rm`, código `/app:ro`, sin tocar servidor operativo. Perfil Chrome independiente en `/tmp/sicon-3a-tabs-chrome-qa`; servidor localhost8788/CDP9238. Sin HTML estático, interceptación de respuestas ni sesión simulada.
- 32 selecciones: ocho pestañas a **1440/1280/768/360px**, una visible cada vez, navegación disponible, selección perceptible, objetivos táctiles y sin overflow horizontal global. Resize mantiene la pestaña activa íntegra en su barra. Capturas inspeccionadas de implementación real con datos sintéticos persistidos.
- Teclado real, roving tabindex, activación manual y salida al panel; hash inexistente/malformado seguro; hash de control individual, refresco, atrás/adelante; POST real de control con retorno contextual, error de foja y texto conservados al cambiar de pestaña; prioridad de error sobre hash viejo. Edición directa de jurado, veedor, aspirante y persona con valores persistidos y retorno correcto. Lector conserva consulta, sin acciones de escritura, POST rechazado403.
- JavaScript deshabilitado: ocho secciones visibles y POST de control con retorno a fragmento; carga bloqueada e inicialización deliberadamente fallida: rollback a HTML completo sin roles interactivos inoperantes. Cero errores inesperados. Dos bloqueos `inspector` del recurso de tabs y un error capturado de inicialización son ensayos deliberados, registrados separadamente, no defectos de producción.
- Hallazgo visual real corregido: al reducir1280→360 con Control seleccionado, el panel seguía activo pero su pestaña quedaba fuera de vista. El callback de layout ahora revela esa pestaña dentro de su barra, sin desplazar horizontalmente la página; regresión geométrica y PNG final lo comprueban.
- Incidencias del arnés, no defectos visuales: comparación errónea de pathname con hash; después, navegar solo a otro hash no recargaba el documento tras deshabilitar scripts. Se pausó y obtuvo auditoría fresca de aislamiento en ambos casos. El arnés verifica pathname/query/hash separados y espera recarga HTTP/load al cambiar disponibilidad de JS. Los bloqueos deliberados se registran con URL y `blockedReason`, sin ignorar errores vacíos.
- Chrome cerrado; servidor propio detenido; `cleanup.txt` confirma TEST destruida. Puertos8788/9238 sin listeners. No se corrió `makemigrations`: no cambian modelos; el pendiente previo de `documentos.DestinatarioPersonal.id` sigue fuera de alcance.

```sh
docker compose run --rm --no-deps -v "$PWD:/app:ro" web sh -c 'python manage.py check && python manage.py test core.tests.test_detail_presentation core.tests.test_auth core.tests.test_concurrency core.tests.test_navigation core.tests.test_workspace concursos.tests.test_concursos participantes.tests.test_participantes participantes.tests.test_ajustes expedientes.tests.test_documental --noinput'
node core/tests/navigation.test.js
node core/tests/detail_tabs.browser.test.js http://127.0.0.1:9238 http://127.0.0.1:8788 /tmp/sicon-3a-tabs-qa
```

El comando de navegador requiere iniciar antes Chrome y el servidor QA exclusivos; ambos se cerraron al terminar. Script de servidor y logs completos quedan en `/tmp/sicon-3a-tabs-qa/`; [registro durable de verificaciones](evidencias/sdd-006/3a/correccion-tabs/verificacion.json).

### Capturas nuevas (las anteriores se preservan)

| Panel | 1440px | 1280px | 768px | 360px |
|---|---|---|---|---|
| Resumen | [Ver](evidencias/sdd-006/3a/correccion-tabs/resumen-1440.png) | [Ver](evidencias/sdd-006/3a/correccion-tabs/resumen-1280.png) | [Ver](evidencias/sdd-006/3a/correccion-tabs/resumen-768.png) | [Ver](evidencias/sdd-006/3a/correccion-tabs/resumen-360.png) |
| Jurados | [Ver](evidencias/sdd-006/3a/correccion-tabs/jurados-1440.png) | [Ver](evidencias/sdd-006/3a/correccion-tabs/jurados-1280.png) | [Ver](evidencias/sdd-006/3a/correccion-tabs/jurados-768.png) | [Identidad](evidencias/sdd-006/3a/correccion-tabs/jurados-360.png) · [Acciones](evidencias/sdd-006/3a/correccion-tabs/jurados-acciones-360.png) |

Otros estados: [retorno de control](evidencias/sdd-006/3a/correccion-tabs/control-retorno-1280.png), error [1280](evidencias/sdd-006/3a/correccion-tabs/control-error-1280.png)/[360](evidencias/sdd-006/3a/correccion-tabs/control-error-360.png), [retorno de aspirante](evidencias/sdd-006/3a/correccion-tabs/aspirante-retorno-1280.png), [barra móvil](evidencias/sdd-006/3a/correccion-tabs/historial-movil-indicador.png), [sin JavaScript](evidencias/sdd-006/3a/correccion-tabs/sin-javascript-1280.png), [lector](evidencias/sdd-006/3a/correccion-tabs/lector-aspirantes-360.png).

### Límites
- Chrome es el navegador comprobado; no se certifican otros motores ni lectores de pantalla. Tablas anchas conservan scroll local accesible, no se convierten en tarjetas ni se ocultan columnas. No se recertifican DOCX, las52 rutas ni otras fases.
- Datos exclusivamente de prueba en PostgreSQL temporal. La generación conservada está vacía en la fixture; sus parciales y lógica permanecen sin cambios, sin afirmar QA de composición documental.
- Revisión independiente focalizada completada, sin hallazgos productivos demostrables. Comparó los 12 archivos contra copias originales verificadas por SHA-256, revisó los retornos internos seguros, formularios sin duplicación, ARIA, errores, historial y registros de QA; inspeccionó ocho capturas. El agente principal inspeccionó además Resumen y Jurados en escritorio/móvil, error documental y barra de Historial. No se recertificaron apertura nativa del select ni todos los estados error/deshabilitado de textarea/select; sus componentes permanecen intactos.
- **Aceptación visual y funcional del usuario pendiente; detenerse aquí, sin3B/3C, commit, push ni despliegue.**
