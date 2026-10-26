## Revisión independiente de maquetación (continuación fuera de Codex)

Se inspeccionó la copia recibida el 23/10/2026 y los cinco PDF institucionales. En un entorno aislado, sin base de datos ni Django, se ejercitó el módulo `documentos/renderers.py` con datos **exclusivamente sintéticos**, reemplazando solo las referencias de clases de dominio necesarias. Los seis tipos DOCX se generaron y se abrieron con LibreOffice; todos se convirtieron a PDF sin errores.

Páginas con ese conjunto sintético: convocatoria **4** tras ajustar el anexo (eran 5), dictamen **2**, designación **3**, elecciones **1**, jurados **1** y APUNSJ **1**. Se revisaron visualmente las primeras páginas y las cuatro páginas de convocatoria, sin detectar superposición ni texto recortado en ese conjunto. Este control no acredita correspondencia jurídica de la redacción ni cubre extremos de longitud, datos reales o todas las variantes.

**Corrección:** el detalle de los doce apartados del anexo de convocatoria utiliza estilo local «Detalle anexo» (10,5 pt, interlineado 1,15, sin sangría inicial). El cuerpo resolutivo conserva el formato existente. Se incrementa exclusivamente la versión de plantilla a `convocatoria-3` para identificar las futuras generaciones sin modificar las almacenadas.

**Limitaciones:** no fue posible instalar Django en este entorno sin conectividad al índice de paquetes, por lo que NO se ejecutó aquí la suite PostgreSQL ni el navegador real. Se verificó la sintaxis de los módulos Python mediante `compileall`. Permanecen pendientes revisión administrativa de fidelidad institucional, oficio APUNSJ definitivo y prueba funcional en la instalación del usuario.

---

# SDD-005 — Recuperación y evidencia de continuación

## Estado vigente
Recuperada tras reinicio accidental de extensiones. Se reutilizaron todos los cambios existentes, sin reset, checkout restaurador ni eliminación de modificaciones. Los cinco PDF ahora están disponibles en `documentos/modelos/`; se inspeccionaron las 19 páginas originales. Se implementaron las cinco salidas faltantes y las seis notas/ZIP sobre el motor recuperado. **Aceptación administrativa, visual Word y funcional del usuario pendientes. APUNSJ sigue PROVISIONAL (`apunsj-1`) y pendiente de validación formal.** No se inició SDD-006 ni ninguna otra fase.

## Diagnóstico de recuperación
| Situación encontrada | Clasificación | Acción de continuación |
|---|---|---|
| Modelos, migración inicial documental, permisos, configuración APUNSJ, conservación de bytes/hash/snapshot y pruebas previas | Completa para la primera entrega | Se conservaron y extendieron; sin migración adicional |
| Catálogo versiones `*-2`, complementos dinámicos y preparación de fuentes/huella | Parcial: no enlazados con vista/template | Se conectaron y revalidaron desde POST; campos críticos requeridos, mensajes accesibles y componentes compartidos |
| Cinco renderers de PDF | Faltantes: `KeyError: elecciones` reproducido por regresión antes de completar | Se reconstruyeron convocatoria/anexo, dictamen, designación, elecciones y notificación |
| Seis notas, ZIP y descarga individual histórica | Faltantes | Un ZIP privado guardado con manifiesto/hashes de seis DOCX; descargas extraen exactamente bytes guardados |
| Pruebas y evidencia de continuación | Faltantes; 164 pruebas anteriores no verificaban estos cambios | Nueva suite de 176 pruebas, muestras y evidencia actualizada |

No se tocó `.atl/` ni los originales PDF. Los cambios de `.atl/` observados al recuperar son preexistentes y ajenos a esta continuación. No se aplicaron migraciones a la base operativa ni se recreó su servicio.

## Funcionalidad disponible
| Documento | Plantilla | Fuentes/datos y límites |
|---|---|---|
| Convocatoria y anexo | `convocatoria-2` | Cinco controles previos, cuatro fojas y seis plazas mediante habilitación central; funciones necesarias para anexo; complementos de antecedentes, presupuesto, inscripción, requisitos, condiciones, publicidad y temario acreditados |
| Notificaciones | `jurados-2` | Exactamente seis notas individuales Letter, representación/calidad y nombre/título registrados; tratamiento opcional explícito por jurado; resolución oficial, fundamento y remitente requeridos; recibí editable sin firma reproducida |
| APUNSJ | `apunsj-1`, PROVISIONAL | Destinatario configurado y versionado; nunca inventa lugar, fecha, número ni firmante; revisión formal pendiente |
| Aprobación de dictamen | `dictamen-2` | Lista real de inscriptos, seis jurados y actuaciones verificadas con fojas; mérito expreso de tamaño variable, resultados y situación de comunicaciones/recursos acreditados |
| Designación | `designacion-2` | Elección expresa de aspirante de este concurso, sin ganador automático; referencias oficiales, efectos y presupuesto acreditados; limitación anterior opcional por decisión expresa y texto completo |
| Elecciones | `elecciones-2` | Solicitud preparatoria, destinatario/remitente explícitos, antecedentes y procedimiento normativo acreditados; no presume elección realizada |

Los complementos críticos faltantes bloquean salida; no se produce «PENDIENTE», marcadores de combinación, artículos vacíos ni hechos de los ejemplos como ciertos. El mérito se ingresa `puesto | ID de aspirante`, sin puestos/personas duplicados, IDs ajenos ni orden de inscripción implícito. Se prueba lista de siete aspirantes, sin el límite de cinco del modelo. No se agrega ningún campo a Concurso.

### Reconstrucción de fuentes y ambigüedades
- Resoluciones: VISTO, CONSIDERANDO, autoridad, artículos, cierre; convocatoria incluye anexo de doce apartados con numeración Word real, salto previo y tabla presupuestaria agrupada de trece columnas más detalles. Dictamen/designación iteran personas reales y mérito suministrado.
- A4 para resoluciones/elecciones; Letter para notas a jurados. Override institucional: resoluciones Arial 12, interlineado 1,5, márgenes 25/15/25/30 mm; notas Arial 11, 1,15 y margen superior 50 mm para separar membrete. Se normalizó tipografía/espaciado sin afirmar fidelidad visual todavía.
- Membrete recortado de fuente sin firmas ni conmemoración fechada. No se incorporan como vigentes nombres/cargos de autoridades de los ejemplos. Recibí son campos editables intencionales de recepción, no datos críticos desconocidos.
- Convocatoria original omite 4 y duplica 8: numeración mecánica consecutiva 1–8 para las ocho disposiciones, sin inventar contenido faltante. Validación administrativa pendiente.
- Inconsistencia «Resolución/Ordenanza 6/14-R» no se decide jurídicamente por intuición: fundamento normativo y circuito exactos son complementos acreditados requeridos. No se presumen unanimidad, ausencia de recursos, jubilación, presencia/entrega de copias, plazos, temarios específicos, códigos presupuestarios ni fechas de posesión.
- Acotado exige confirmación expresa y fundamento normativo acreditado. No se insertan por defecto requisitos de Cerrado Interno o normas ordinarias como marco suficiente.

## Seguridad e integridad
GET no genera y POST conserva CSRF. Requiere `concursos.view_concurso` y `documentos.generar_documento`; configurar APUNSJ mantiene permiso específico. Huella obligatoria de revisión incluye fuentes pertinentes del concurso, personas, participaciones, controles, hash PDF y versión de plantilla. Bajo transacción se bloquean/revalidan antes de componer. Tratamientos y complementos se guardan en snapshot. Bytes privados y hashes históricos no cambian al editar fuentes. Descarga conjunta/individual comprueba concurso y hash, usa nombres internos fijos y nunca invoca el renderer.

Generar no modifica estados, controles, fojas, historial, participantes ni actos oficiales. No firma, notifica, publica o incorpora documentación al expediente; sin integración CoPla. Se conserva control servidor de inactividad real. Sin logs de datos personales de fuentes.

## Pruebas ejecutadas tras la recuperación
Regresión RED inicial ejecutada sobre código recuperado:
```sh
docker compose run --rm --no-deps -v "$PWD:/app:ro" web sh -c 'python -c "import docx" || pip install python-docx==1.2.0; python manage.py test documentos.tests.ContinuacionDocumentosTests.test_elecciones_fuente_presente_genera_nota_editable -v 1'
```
Resultado: una prueba con ERROR `KeyError: 'elecciones'`, confirmando el punto de interrupción. Se completó el renderer; no se reinició la implementación.

Verificación completa posterior en contenedor desechable con PostgreSQL de pruebas (código actual montado solo lectura):
```sh
docker compose run --rm --no-deps -v "$PWD:/app:ro" web sh -c 'pip install -q python-docx==1.2.0 && python -m pip check && python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test -v 1'
git diff --check
```
- **176 pruebas OK, 25,703 s** (repetición final; primera pasada completa 24,431 s), base de pruebas creada y destruida. Incluye **32 pruebas documentales** (20 recuperadas y 12 nuevas) y 144 previas del resto de aplicaciones.
- `pip check`: **No broken requirements found.** Django: **System check identified no issues (0 silenced).** Migraciones: **No changes detected.** `git diff --check`: sin incidencias.
- Cobertura nueva: cinco fuentes presentes, salidas completas sin hechos de ejemplo, estructura Word A4/Letter, anexo/tabla, siete aspirantes y mérito expreso, seis notas reales y ZIP/descargas byte a byte, conservación al cambiar persona, complementos vacíos/XML inválido, mérito duplicado/ajeno, selección expresa, limitación opcional, fuentes/personas/jurados/aspirantes/controles/versiones obsoletas, POST integrado de cinco salidas, permisos/CSRF/sesión vencida y ausencia de efectos administrativos.
- Falla intermedia corregida: restar dimensiones python-docx produce `int`; se envuelve `Emu` antes de `.twips`. Una regresión de huella elegía una Persona aspirante al probar documento que solo usa jurados: se acotó el fixture a una fuente pertinente (minimización de datos).
- La imagen Compose existente no incluye `python-docx` ni monta el código actual. La instalación de dependencia ocurrió únicamente dentro del contenedor `--rm`, no en host/proyecto ni servicio persistente. No ejecutar `migrate` contra base operativa durante esta verificación.

## Muestras actuales y límite de QA visual
Muestras exclusivamente sintéticas en `/private/tmp/sdd005-recovery/samples/`: `convocatoria.docx`, `dictamen.docx`, `designacion.docx`, `elecciones.docx`, `apunsj.docx`, `jurado-1.docx` a `jurado-6.docx` y `jurados.zip`. `manifest.json` registra tamaño, SHA-256 y versión. Todos fueron abiertos con python-docx; se comprobó edición/guardado de las salidas no agrupadas y apertura de las seis notas. Prueba independiente de generación de muestras: **1 OK, 0,677 s**, con base test creada/destruida.

Se ejecutó el `render_docx.py` de la skill en contenedor desechable, instalando solo ahí `pdf2image==1.17.0`:
```sh
python /docx-skill/render_docx.py /qa/samples/convocatoria.docx --output_dir /qa/render-convocatoria
```
Resultado: **FileNotFoundError: [Errno 2] No such file or directory: 'soffice'**. No se instaló LibreOffice ni herramientas pesadas. No se generaron PNG Word; no se afirma validación visual, paginación final ni fidelidad Word a los PDF.

No hay herramientas de navegador ejecutables expuestas en esta sesión. La UI nueva se comprobó mediante render de templates/cliente Django, componentes compartidos y pruebas de POST/error; **responsive, foco y apertura de selects nuevos requieren revisión real pendiente**. Las capturas Chrome de la primera entrega, conservadas debajo, son evidencia histórica, no de la UI ampliada.

## Pendientes vigentes
1. Revisión independiente de backend, seguridad y UI coordinada por el orquestador; no se simula ni se declara ya realizada.
2. Abrir/renderizar muestras Word y aprobar redacción, estructura, tablas, numeración/paginación y fidelidad institucional. QA OOXML no sustituye esta revisión.
3. Validación formal del oficio APUNSJ provisional y ambigüedades administrativas indicadas; pruebas visuales de nuevos formularios en navegador.
4. Aceptación funcional del usuario. No avanzar de fase ni hacer commit, push o despliegue. Nueva migración documental sigue pendiente de autorización operativa en base persistente.

## Archivos de continuación
`documentos/{forms,registry,services,renderers,views,urls,tests}.py`, `documentos/assets/unsj-crest-wordmark.png`, `templates/documentos/{revision,seccion}.html`, spec y `SDD-005-EVIDENCIA.md`, `README.md`, PRODUCTO, DECISIONES, ROADMAP, ARQUITECTURA y FUENTES. Modelos, migración e integración existentes se preservaron, sin reescribir Concurso, autenticación o CSS compartido.

---

**Registro preservado de la primera entrega:** los bloqueos por fuentes y pendientes de implementación que siguen se refieren exclusivamente al estado anterior al reinicio; el estado vigente y las pruebas que lo acreditan están arriba.

# Registro histórico previo al reinicio (no acredita la continuación)

## Estado y límites
Autorizada el 23/10/2026, con aceptación expresa de SDD-001 a SDD-004. **No cumple aún toda la aceptación de SDD-005.** No están disponibles los cinco modelos PDF enumerados en `FUENTES.md`. No se inventaron su texto ni su formato. No se implementa otra fase, integración CoPla, PDF, firma, emisión o notificación.

## Documentos y variables
| Tipo | Automáticas | Complementarias | Pendientes / disponibilidad |
|---|---|---|---|
| Convocatoria | Concurso, seis jurados, documentación y fojas | Tratamientos y lo que requiera la fuente | Bloqueado: modelo original. Consulta central de habilitación muestra además cinco controles, cuatro fojas, seis plazas y datos generales faltantes |
| Notas a jurados | Concurso, persona, título, unidad, representación y calidad | Tratamientos según fuente | Bloqueadas: fuente y resolución oficial estructurada; seis notas y ZIP pendientes |
| Oficio APUNSJ | Datos del concurso y destinatario institucional | Confirmación de revisión administrativa para Acotado | Disponible como BORRADOR NO EMITIDO `apunsj-1`; lugar, fecha, oficio y firmante explícitamente no incorporados |
| Aprobación de dictamen | Concurso, jurados, aspirantes y actuaciones verificadas | Evaluaciones, resultados, mérito, comunicaciones e impugnaciones acreditadas | Bloqueado: fuente y antecedentes oficiales no registrados |
| Designación | Concurso y antecedentes documentales | Persona propuesta, resultado, mérito y efectos acreditados | Bloqueado: fuente y antecedentes oficiales no registrados; no selección automática |
| Elecciones del personal | Concurso y estructura | Destinatarios y autoridades específicos | Bloqueado: fuente original; no resultados electorales presumidos |

La matriz está centralizada en `documentos/registry.py`. Los cinco tipos bloqueados son límites reales, no salidas sintéticas. La nota de elecciones reemplaza el acta de sorteo del alcance original; se conserva la spec existente `specs/005-generacion-docx.md`.

## Configuración, seguridad y antecedentes
Destinatario APUNSJ único: Sr./Sra., cargo concordante, título opcional, nombre y apellido. Permiso `documentos.configurar_institucion`, versión esperada y bloqueo evitan sobrescritura. Generación/descarga requiere `concursos.view_concurso` + `documentos.generar_documento`; no se asignan automáticamente a usuarios o grupos.

GET muestra revisión, no genera. POST con CSRF revalida disponibilidad y versiones. Todos los endpoints están bajo `/concursos/` y conservan sesión existente. Almacena bytes Word privados, SHA-256, snapshot de datos usados y actuaciones verificadas, plantilla, autor y fecha. Descarga verifica concurso/documento y retorna bytes históricos, nunca regenera. No hay rutas arbitrarias, temporales, medios públicos ni transmisión externa. La inmutabilidad de API/ORM no reemplaza permisos administrativos de base.

Generar no modifica estados, checklist, fojas, jurados, veedores, aspirantes ni actos oficiales. Un veedor no designado no bloquea el oficio. Acotado requiere confirmación explícita de revisión administrativa y queda registrado; no existe modelo específico aprobado.

## Verificación automatizada
Ejecución final sobre PostgreSQL de pruebas desechable, con el código del repositorio montado en `/app`, sin aplicar migraciones a la base persistente:
```sh
pip install python-docx==1.2.0
pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 1
```
- **164 pruebas OK**, 21,658 segundos; base de pruebas creada y destruida. Son 20 pruebas documentales nuevas, además de la suite previa.
- `pip check`: No broken requirements found. `check`: sin incidencias. Migraciones: No changes detected. `git diff --check`: limpio.
- Cobertura documental: Word OOXML editable y guardado tras edición, encabezados Secretario/Secretaria, ausencia de placeholders, campos faltantes/cargo incompatible, permisos separados, versiones obsoletas, bytes/hash/snapshot conservados, no efectos administrativos, fojas verificadas, cinco bloqueos por fuentes y servicio central de convocatoria, revisión Acotado, acceso cruzado, CSRF, GET sin generación, descarga sin regeneración, sesión vencida, errores controlados, selectors iniciales vacíos y navegación accesible.
- Hallazgos de revisión corregidos y con regresiones: impedir reemplazo de una generación reconstruyendo una instancia con PK existente; rechazar caracteres de control XML inválidos en texto de concurso/configuración con mensaje comprensible y sin guardar una generación; nombre de documento histórico desde el catálogo único y navegación activa/`aria-current` en revisión/configuración.
- Dos fallos intermedios fueron de pruebas: relación existente `veedors` y conteo demasiado estricto de un título también presente en el checklist; ambos corregidos, suite final verde.
- No se prueba fidelidad, seis notas/ZIP o mérito variable en salidas bloqueadas: todavía no se implementaron. Las pruebas existentes de expedientes cubren jurados y habilitación documental.

## Muestras y revisión visual
Muestras fuera del repositorio, con datos exclusivamente sintéticos, compuestas por el renderer real y abiertas con `python-docx`:
- `/private/tmp/sdd005-apunsj-sr.docx`: 38.586 bytes, encabezado Sr. Secretario General de APUNSJ.
- `/private/tmp/sdd005-apunsj-sra.docx`: 38.588 bytes, encabezado Sra. Secretaria General de APUNSJ.

Esto acredita estructura OOXML y editabilidad, **no** maquetación visual Word. Se intentó `render_docx.py` empaquetado: en el host faltó `pdf2image`; se repitió dentro de un contenedor desechable con `pdf2image==1.17.0` como herramienta temporal. La lectura de OOXML fue correcta, pero la conversión falló con `FileNotFoundError: soffice`: no hay LibreOffice disponible. No se instalaron dependencias de render en el proyecto ni se produjeron PNG/PDF. No se afirma revisión visual Word ni fidelidad a PDF no inspeccionados. La aprobación visual de muestras Word permanece pendiente. La verificación de la interfaz en Chrome se documenta a continuación.

### Interfaz: verificación real en Chrome
- Los cinco tipos sin fuente aparecen bloqueados e identifican el nombre del modelo faltante. APUNSJ sin destinatario configurado no ofrece generación habilitada.
- Configuración: se guardaron correctamente Sr./Secretario General y Sra./Secretaria General; se rechazó la combinación incompatible. Los errores requeridos se asociaron mediante ARIA.
- Navegación real con Tab: foco naranja visible en los controles. La revisión identifica el carácter de borrador y los datos pendientes.
- La generación por POST produjo una descarga DOCX con HTTP 200 y `Content-Disposition: attachment`.
- Sin desbordamiento horizontal de página en 1440, 1280, 768 y 360 px. Capturas de evidencia fuera del repositorio: `/private/tmp/concursos-sdd005-*.png`.
- **Limitación puntual:** no se capturó visualmente el menú nativo del select abierto. No se da ese aspecto por validado. Esta comprobación de interfaz no sustituye la revisión de maquetación Word ni la fidelidad pendiente a las fuentes originales.

## Migración y actualización
Nueva migración `documentos/0001_initial.py`, solo tablas documentales y permisos. No modifica Concurso ni actúa sobre datos anteriores. No se aplicó a la base persistente.

Para actualizar el entorno, con autorización operativa posterior: reconstruir web para instalar `python-docx==1.2.0`, ejecutar `python manage.py migrate` en el entorno elegido y otorgar explícitamente los dos permisos documentales a las cuentas autorizadas. Luego configurar APUNSJ desde Configuración institucional. No se realizó commit, push ni despliegue.

## Archivos principales
- `documentos/{models,forms,registry,renderers,services,views,urls}.py`, `apps.py`, migración y `tests.py`.
- `templates/documentos/`: sección de ficha, revisión y configuración, con componentes compartidos y sin CSS específico.
- `config/settings.py`, `config/urls.py`, `concursos/views.py`, ficha y navegación: integración acotada.
- `requirements.txt`: `python-docx==1.2.0` (PyPI oficial, publicado 16/06/2025, Python >=3.9).
- Spec, PRODUCTO, DECISIONES, ROADMAP, ARQUITECTURA y README: alcance real, límites e instrucciones operativas.

## Pendientes de aceptación
1. Recibir las cinco fuentes originales y validar redacción, datos complementarios y reconstrucción institucional.
2. Completar cinco tipos bloqueados y ZIP; no afirmar hechos no acreditados.
3. Abrir/renderizar muestras Word y aprobar su formato visual; completar la comprobación visual del menú nativo del select abierto.
4. Aceptación funcional del usuario. Detenerse aquí; no avanzar de fase.


## Corrección focalizada posterior: convocatoria sin funciones y revisión guiada

- `Concurso.funciones` ya era opcional. Se eliminó el bloqueo documental redundante en `faltantes_antecedentes`.
- La resolución y su anexo omiten el renglón de funciones si está vacío; si hay funciones, se conserva su inclusión.
- La revisión de convocatoria distingue el resumen de datos maestros, la disponibilidad documental y cuatro grupos de datos específicos: antecedentes, publicidad/inscripciones, condiciones/temario y presupuesto. El usuario puede volver directamente a la ficha, jurados y control documental.
- No se duplicaron datos, no se creó persistencia nueva y se conservaron las validaciones y el historial de borradores existentes. Los complementos documentales siguen ingresándose para cada generación.
- Se agregaron pruebas de regresión para ambas variantes del campo funciones y para la presentación única de cada complemento.
- Este ajuste no requiere migraciones. La batería completa Django/PostgreSQL debe ejecutarse en la instalación local, ya que no se pudo ejecutar en el entorno de preparación del parche.


## Corrección de datos maestros y afectación presupuestaria (revisión funcional)

- Concurso: se incorporan como datos persistentes opcionales el ex titular, fecha y motivo de baja, resolución de baja con formato exacto `NNNN/NN-R`, y tratamiento, nombre y cargo de quien inicia el expediente.
- Las plantillas de convocatoria, designación y nota de elecciones recuperan los datos anteriores sin pedir que se repitan en cada revisión. No se presume que la baja sea por jubilación.
- Control documental: la afectación presupuestaria permite guardar códigos de partida principal y actividad de dos dígitos (un dígito se normaliza con cero inicial), con auditoría y concurrencia existentes.
- Atención: en el PDF fuente se distingue la unidad principal (PPAL) de la partida principal del gasto (`1.1` en el ejemplo). No se mapea automáticamente un nuevo código de dos dígitos a la línea `PARTIDA PPAL` del DOCX hasta validar su correspondencia.
- Migraciones aditivas: `concursos.0004` y `expedientes.0005`; no se modifica el catálogo de 21 requisitos ni se eliminan datos históricos.
- Se agregan pruebas de validación de campos, persistencia, auditoría de los códigos y generación con antecedentes. La suite Django/PostgreSQL debe verificarse en la instalación local.


### Ajuste de simplificación de convocatoria

La revisión solo solicita fecha de apertura (entrada de fecha real) y lugar de informes.
Los textos institucionales y el presupuesto se arman desde la fuente fija y los campos del expediente.
Se agrega turno y domicilio de trabajo en concurso, con migración aditiva `concursos.0005`.
El código presupuestario PPAL (2 cifras) se distingue de la partida del gasto `1.1`.
La documentación de la convocatoria debe revisarse administrativamente, en particular
para modalidades distintas de Cerrado Interno y frente a cambios normativos posteriores.


## Ajuste de convocatoria: plantilla consolidada revisada párrafo por párrafo

- Se incorporaron la jurisdicción (Rectorado o los tres IPU), artículos editables por campo,
  causa de vacancia (siete variantes), acto administrativo y detalle de otra causa.
- Los nombres de unidades y dependencias permanecen sin artículos; el motor compone
  «en el», «en la», «del», «de la» sin concatenaciones inválidas.
- La cabecera identifica «Funciones» con la **denominación del cargo**. No repite el código
  de agrupamiento y no necesita descripción opcional de funciones.
- Ocho considerandos y ocho artículos con la redacción acordada; cláusula de vacancia
  específica según causa seleccionada, sin presumir jubilación.
- Anexo con 12 apartados: Rectorado primero, luego autoridad de dependencia que convoca,
  finalmente personal de dependencia; temario general solo como título editable.
- Solo fecha de apertura es complementaria en la revisión de convocatoria.
  Jurisdicción, domicilio, turno, iniciador y vacancia pertenecen al concurso; las fojas
  y los códigos PPAL/ACTIV se leen de Control documental.
- La tabla mantiene «PARTIDA PPAL: 1.1» fija, distinta del PPAL de dos dígitos.
- Los concursos existentes conservan sus datos anteriores; deberán completar nuevos
  antecedentes antes de generar una convocatoria con la nueva plantilla.
- **Pendiente**: ejecutar la suite PostgreSQL y revisar visualmente un DOCX real generado
  en SiCon. El parche no altera documentos ya generados y almacenados.


## Ajuste: notificaciones sin carga documental duplicada

- La resolución oficial de convocatoria se registra en la ficha del concurso
  (`resolucion_convocatoria`, formato `NNNN/NN-R`) tras su emisión efectiva.
- En la revisión de jurados ya no se solicitan número de resolución, lugar/fecha
  ni tratamientos individuales: las seis participaciones y el membrete se recuperan
  del sistema; «San Juan» y la fecha de preparación se insertan automáticamente.
- No se infiere género a partir del nombre; se mantiene `designado/a` editable en el DOCX.
- La ausencia de un número oficial bloquea las notificaciones sin afectar
  convocatoria, otros documentos ni el estado del concurso.
- La huella de fuentes incluye el número oficial; los documentos históricos y sus
  copias de datos permanecen inmutables ante modificaciones posteriores.
- Migración aditiva: `concursos.0007_resolucion_oficial_convocatoria`.
- Pruebas de validación, ausencia de campos duplicados, conservación histórica,
  permisos y cambios concurrentes incluidas. Requiere verificación Django/PostgreSQL
  en la instalación local.


### Corrección: oficios preparatorios previos a convocatoria
- La nota de elección de representantes del personal utiliza el PDF `Nota para elecciones por el estamento.docx.pdf`: conserva los párrafos fijos y sustituye los hechos particulares del ejemplo por antecedentes del concurso.
- Nuevo oficio provisional al Rector para indicar jurados titular y suplente. No afirma designación.
- Jefatura de Personal configurable por permiso `documentos.configurar_institucion`.
- Se reutiliza el membrete institucional vigente para ambos oficios y se conserva su versión, hash y contenido en las generaciones históricas.
- Los dos documentos se generan antes de la resolución de convocatoria, sin alterar el checklist ni los estados.

- Ajuste tipográfico posterior: plantillas `elecciones-5` y `jurados-rectorado-2`: ambos oficios preparatorios generan el texto editable (fecha, destinatario, cuerpo y firma) exclusivamente en Arial 11. El membrete cargado conserva la tipografía que tenga incorporada en la imagen. Sin migraciones adicionales.
