# Registro de decisiones y pendientes

## Acordado
- Aplicación independiente de CoPla, destinada a Dirección de Concursos Nodocentes de la UNSJ.
- Identidad visual **Blanco y naranja**, con tokens fijos de `docs/DISEÑO.md`.
- Criticidad máxima de consistencia visual, reutilización y buenas prácticas Django.
- Autenticación con cierre por 30 minutos sin actividad real y respaldo en servidor.
- Estados principales y situaciones independientes; cambios sugeridos, jamás automáticos, y cambio manual con historial.
- Jurados: titular/suplente de tres representaciones. Veedores: APUNSJ, no bloquean trámite. Aspirantes: nombre, apellido, DNI.
- Cinco requisitos previos que habilitan el **proyecto** de resolución de convocatoria, sin importar el orden de llegada.
- Checklist habitual de 21 requisitos, con foja solo donde se indicó.
- DOCX editable y separación de proyecto, documento oficial y check del expediente.
- Dos integraciones futuras CoPla; la aplicación funciona sin ellas.

## Pendiente de validación antes de fases correspondientes
- Obligatoriedad exacta de campos adicionales de convocatoria y alcance de unicidad de expediente.
- Catálogos de modalidades, agrupamientos y permisos/roles de operación.
- Casos extraordinarios (impugnaciones, suspensión, recusación, sustitución, desierto, anulaciones) y sus actuaciones.
- Fechas/hitos de notificación del dictamen y sus plazos, a considerar en checklist operativo.
- ¿Cuándo se considera administrativamente «Finalizado»? Resolución emitida vs toma de posesión/cierre.
- Modelo definitivo de personas y fotografía histórica para documentos.
- Disponibilidad y naturaleza editables de las plantillas: se aportaron PDF que deben recrearse/verificarse como DOCX.
- Contrato API con CoPla, ejecución atómica o secuencial de múltiples movimientos y actos habilitantes.

No convertir estos pendientes en reglas definitivas sin nueva decisión administrativa.

## SDD-002 — Criterios confirmados por el usuario (22/10/2026)
- Expedientes repetidos permitidos mientras no se defina el ámbito de unicidad.
- Datos mínimos de la especificación obligatorios; tipo/modalidad, agrupamiento, categoría y tramo como texto libre. Sin campos complementarios en esta fase.
- Permisos nativos separados para consulta, alta, edición de datos y cambios manuales de estado/situación, sin roles nuevos ni eliminación de concursos.
- Los pendientes de catálogos, unicidad futura y campos complementarios siguen abiertos para una decisión posterior.

## Ajustes SDD-002/003 confirmados (23/10/2026)
- Correo y expediente de inscripción opcionales por inscripción de aspirante; no pertenecen a Persona.
- DNI de 8 dígitos y expedientes `99-NNNN-9999` (central 1–9999 sin relleno), con máscaras compartidas y validación Django. Expedientes repetidos permitidos con advertencia entre concursos.
- Funciones del cargo es opcional y complementaria, conservada sin reemplazos automáticos para futura generación documental.
- Compatibilidad técnica: no migrar/rellenar identificadores históricos ni reducir columnas; admitir el valor anterior sin cambios al editar su registro y exigir formato nuevo al modificarlo. Una corrección de DNI compartido sigue sujeta a la protección de SDD-003.
- SDD-004 continúa sin autorización; estos cambios requieren aceptación de la entrega ajustada.

## Consolidación SDD-002/003 — catálogos locales (23/10/2026)
Decisión del usuario que sustituye el texto libre inicial de modalidad, agrupamiento, categoría y tramo. No cambia participantes ni habilita SDD-004.

### Tipos y fundamento normativo
Cuatro modalidades obligatorias mediante TextChoices: Cerrado Interno, Cerrado General y Abierto ([Ordenanza 33/10-CS](https://www.ffha.unsj.edu.ar/wp-content/uploads/2022/10/ORD-33-2010-CS-Reglamento-de-Concursos-PAU.pdf)), más Acotado ([Ordenanza 37/25-CS, Anexo, art. 14, página 8 del PDF](https://digesto.unsj.edu.ar/admin/digesto_admin/pdf/ORD37O-2512511.pdf#page=8)). El artículo fue verificado en la publicación del Digesto enlazada por la Guía de Trámites de UNSJ. Acotado corresponde a impugnaciones procedentes del procedimiento especial de regularización Nodocente con ATF y comprende a impugnantes y persona impugnada. Solo referencia informativa; no implica que toda impugnación de concurso sea un concurso acotado ni implementa admisibilidad, aspirantes o requisitos especiales.

### Evidencia de CoPla y matriz adoptada
Inspección de solo lectura en `C:/Users/Usuario/Desktop/control-planta`: `datos/agrupamientos_iniciales.json`, `src/aplicaciones/agrupamientos/models.py` y comando `cargar_agrupamientos`, `src/aplicaciones/cargos/normativa.py`, `models.py`, `formularios.py`, vistas dependientes y `tests/test_cargos.py`. Su `docs/especificaciones/registro-de-decisiones.md`, DEC-054, declara la matriz completa aprobada y supera los pendientes de documentos anteriores de agrupamientos. Los códigos son institucionales UNSJ, no una transcripción literal de códigos del decreto. Referencia general: [Decreto 366/2006, arts. 47–51](https://www.argentina.gob.ar/normativa/nacional/decreto-366-2006-115242/texto).

| Código | Denominación | Mayor | Intermedio | Inicial |
|---|---|---|---|---|
| 01 | Administrativo | 1, 2, 3 | 4, 5 | 6, 7 |
| 2A | Técnico-profesional | 1, 2, 3 | 4, 5 | — |
| 2B | Técnico-profesional | 2, 3 | 4, 5 | 6, 7 |
| 03 | Mantenimiento, producción y servicios generales | 2, 3 | 4, 5 | 6, 7 |
| 4A | Asistencial | 2, 3 | 4, 5 | 6 |
| 4B | Asistencial | 2, 3 | 4, 5 | 6, 7 |
| 4C | Asistencial | 1, 2, 3 | 4, 5 | 6, 7 |
| 4D | Asistencial | 3 | 4, 5 | 6, 7 |

Adoptada como JSON local versionado en Concursos; no importa código ni consulta datos de CoPla. Sin ABM de catálogos. El tramo no es elegible: deriva de agrupamiento y categoría, incluida categoría 5 de 2A como Intermedio. Python entrega la matriz resuelta a JS; sin reglas de clasificación paralelas en JS ni endpoints/polling adicionales.

### Compatibilidad y criterio conservador
Antes de modificar los modelos se consultaron únicamente los cuatro campos de clasificación y su cantidad en la base local de SiCon: un concurso con Cerrado Interno, Mantenimiento/Producción/Servicios Generales, categoría 5, tramo Intermedio. Correspondencia inequívoca con `cerrado_interno` y código `03`; preflight posterior de solo lectura confirmado para ese registro. No se consultó la base de CoPla.

Migración atómica con preflight de todos los registros. Acepta códigos o denominaciones inequívocas, con normalización de mayúsculas y espacios; no adivina subdivisiones. «Técnico-profesional» sin código puede ser 2A o 2B y «Asistencial» puede ser 4A–4D: bloquean la migración. Lo mismo una modalidad desconocida, categoría no habilitada o tramo previo incompatible. Solución conservadora: conservar la base intacta y resolver el código/correspondencia de cada caso con el responsable administrativo antes de reintentar; no hay valor por defecto.

`clasificacion_anterior` conserva exactamente los cuatro textos previos de registros migrados, sin exponerlos como entrada de formulario. No se reducen columnas ni se tocan CP, denominación, funciones, estructura, auditoría, historial o participantes. La reversión restaura originales si la clasificación continúa igual a la migrada; si fue corregida después conserva la decisión posterior. Las altas posteriores conservan códigos que los campos de texto anteriores admiten. Antes de aplicar esta migración se debe detener el servicio de escritura, para impedir cargas simultáneas de la versión anterior durante la conversión.

## Ajuste puntual SDD-003 — Unidad del jurado (23/10/2026)
- Por pedido del usuario, Unidad reemplaza a Cargo como dato obligatorio de alta y edición de jurados. Es el destino organizativo donde presta servicios el integrante, propio de su participación en cada concurso; puede diferir de la dependencia del cargo concursado.
- Cargo deja de ser entrada de formulario y pasa a ser opcional en el modelo, sin eliminar columna ni valores anteriores. La ficha conserva su consulta diferenciada como dato registrado anteriormente.
- No existe una correspondencia aprobada entre el cargo anterior y la unidad. La migración agrega unidad vacía a jurados anteriores, que deberá completarse al editarlos; no copia cargo, unidad o dependencia del concurso. No cambia datos de identidad/contacto, representación/calidad, permisos ni concurrencia. Aspirantes y veedores quedan fuera de este ajuste.

## SDD-004 — Control documental autorizado (23/10/2026)
- La instrucción expresa de implementación acepta SDD-001, SDD-002 y SDD-003, incluidos sus ajustes, y sustituye las menciones históricas anteriores a la falta de autorización de SDD-004. SDD-005 continúa sin autorización. Esta entrega queda pendiente de aceptación funcional.
- Catálogo ordinario de 19 identificadores estables, agrupados en cinco secciones; no incorporar requisitos por modalidad, impugnación o reglas extraordinarias. «Tres temas» es un solo control. Una única definición Python alimenta modelos/forms, presentación y servicios; migraciones congelan su propio estado histórico.
- **Decisión aclarada por el usuario:** elegir manualmente la etapa documental activa; sus requisitos y los anteriores quedan pendientes exigibles. Los posteriores sin completar se muestran neutrales, sin plazos inferidos. Inicializar en Preparación, sin interpretar el estado administrativo de registros anteriores. Se permite corregir/retroceder etapa, conservando todo lo cargado y una bitácora de cambios de etapa independiente.
- Habilitación del proyecto de convocatoria: cinco controles previos completos, cuatro referencias válidas de fojas, seis plazas correctamente asociadas y con identificación/título/unidad según SDD-003, y datos generales válidos conforme a las reglas ya existentes. No exigir contacto opcional ni inferir la unidad de jurados históricos. Veedores y cantidad de aspirantes no intervienen en esta comprobación.
- Guardar una verificación sin foja requerida admite una carga parcial; no la convierte en requisito completo ni habilita convocatoria. Referencia malformada se rechaza. Fojas como texto canónico, enteros ASCII positivos individuales o rango ascendente; normalización de espacios y ceros de la referencia, sin máscaras ni reglas para expedientes/DNI añadidas.
- Último verificador/fecha se actualizan al modificar un control marcado. Al desmarcar se conserva esa verificación histórica, junto al nuevo editor/fecha y el evento de corrección. Instantáneas antes/después y versión impiden presentar una corrección como dato original. Guardar sin cambios no fabrica historia.
- Etapa y controles usan el permiso explícito `expedientes.change_controldocumental` además de consulta, diferente del permiso de estado. No hay permisos automáticos, altas/bajas manuales de requisitos, eliminación de historial ni registro de estos modelos en admin. Mantener sesiones, CSRF y búsquedas anidadas de concurso.
- Sugerir únicamente Con dictamen cuando el dictamen tiene check y fojas válidas, desde estados anteriores. La publicación no prueba la emisión de una resolución oficial; no sugiere Convocado. La aceptación de la sugerencia pasa por el mecanismo explícito de estado y su historial. No se definen nuevas condiciones para Finalizado.
- Las dos migraciones de expedientes agregan tablas/controles/seguimiento; no reescriben Concurso, personas, participaciones, expedientes ni historial administrativo. Inicialización sin usuarios/verificaciones ficticios; las correcciones posteriores tienen auditoría atómica y concurrencia por registro. Aplicadas en pruebas PostgreSQL, pendientes en la base persistente. Imagen local reconstruida sin recrear el servicio activo.

## Corrección funcional SDD-004 — Convocatoria (23/10/2026)
- El catálogo pasa de 19 a 21 controles, conservando cinco bloques. Tras publicación se presentan oficio a APUNSJ solicitando veedor y notas de notificación a jurados; ambos obligatorios desde Convocatoria, sin foja y de carga en cualquier orden. Notificaciones es un único control general para los seis jurados.
- Los cinco requisitos previos al proyecto de convocatoria no cambian. La ausencia de veedor designado no bloquea el avance; controlar el oficio de solicitud sigue siendo obligatorio. La futura generación en SDD-005 no implica verificación automática.
- Migraciones aditivas nuevas de esquema y datos, con carga idempotente de los dos faltantes, sin recrear ni actualizar los 19 controles previos, etapa o historiales. Reversión solo de semillas nuevas intactas; detenerse si se utilizaron para preservar sus datos/bitácoras. No aplicar en base persistente durante esta corrección.

## SDD-005 — fuentes, recuperación y conservación (23/10/2026)
- El pedido expreso acepta SDD-001 a SDD-004 y autoriza SDD-005. Se conserva `specs/005-generacion-docx.md`, único archivo existente, aunque el pedido lo nombra `005-documentos.md`. Nota para elección de representantes reemplaza el acta de sorteo en el catálogo de seis tipos.
- La entrega inicial se limitó a APUNSJ por fuentes no accesibles entonces. En la recuperación los cinco PDF ya están disponibles en `documentos/modelos/`, fueron extraídos e inspeccionados en sus 19 páginas; se autoriza completar las salidas reutilizando el motor. APUNSJ permanece provisional y pendiente de validación formal.
- `python-docx==1.2.0` compone Word editable en memoria, con helpers compartidos. Los bytes se conservan en registro protegido de base de datos, junto a snapshot JSON, SHA-256, versión y autor/fecha. Sin rutas de disco arbitrarias, media pública, registros editables ni administración de borrado; no se crean campos generales nuevos en Concurso. Inmutabilidad a nivel de API/ORM normal, no mecanismo contra administradores directos de la base.
- Configuración de APUNSJ única, con versión esperada y bloqueo para prevenir sobrescrituras; no catálogo general de organismos. Permisos explícitos e independientes para configuración y generación/descarga, sin asignación automática a roles existentes.
- No existen campos estructurados de tratamiento de jurados ni número/fecha de resolución oficial. Checklist no prueba emisión ni permite inferir esos valores. Quedan pendientes del modelo/documento correspondiente, no se inventan campos ni hechos.
- No existe modelo Acotado aprobado: advertencia y confirmación expresa de revisión administrativa, registrada en la instantánea; no se interpreta normativa para suplir la fuente faltante.

### Recuperación SDD-005 tras reinicio de extensiones
- Se preservó el trabajo existente: modelos, migración, configuración, permisos, snapshots, motor APUNSJ y cambios parciales en catálogo/formulario/servicio. La regresión inicial reprodujo el renderer ausente antes de completarlo.
- Formularios por tipo y huella obligatoria de revisión enlazan cambios existentes; se revalidan fuentes pertinentes bajo transacción. Complementos críticos requeridos sustituyen cualquier salida «PENDIENTE» o hecho de ejemplo.
- Un registro de generación `jurados` conserva el ZIP y manifiesto de seis notas con SHA-256 individual. La descarga individual extrae exactamente los bytes guardados; no necesita modelos nuevos ni regeneración a demanda.
- Las fuentes contienen numeración defectuosa y hechos no universales. Se normaliza mecánicamente convocatoria a ocho artículos consecutivos, sin inventar artículo faltante; se explicita aprobación pendiente. Las referencias contradictorias a 6/14-R se resuelven con texto institucional acreditado, no con una regla jurídica inferida. No se automatizan jubilación, ausencia de recursos, unanimidad, plazos, limitaciones ni selección de ganador.
- Reconstrucción con Arial 12, interlineado 1,5, resoluciones A4 y notas de jurado Letter; membrete sin firma ni conmemoración fechada. Anexo de doce apartados y presupuesto con agrupaciones de trece columnas. Ajustes tipográficos, redacción y numeración requieren aceptación administrativa/visual.
- No se aplican migraciones a la base persistente ni se reconstruye/recrea su servicio. Las pruebas se ejecutan en contenedores desechables con código montado solo lectura y base PostgreSQL de pruebas creada/destruida.


### SDD-005 | Simplificación de convocatoria (23/10/2026)

- La revisión del proyecto de convocatoria requiere **solo** fecha de apertura de inscripciones y lugar para solicitar mayores detalles.
- En el concurso se registran turno de trabajo (mañana: 7 a 14; tarde: 14 a 21) y domicilio de trabajo opcional. Si falta turno, el generador señala cómo completarlo.
- Inscripciones: 8 a 12 hs durante cinco días hábiles desde la fecha indicada, sin calcular una fecha de cierre que podría depender de feriados.
- El marco normativo 33/10-CS y 20/11-CS, el órgano que resuelve (Rector), la intervención SAF, la remuneración, la publicidad, las probanzas y la oposición se resuelven mediante textos de plantilla. No se solicita firmante ni lugar/fecha del borrador de convocatoria.
- Los integrantes del jurado de personal y sus fojas se recuperan de participantes y control documental.
- Requisitos particulares y temarios quedan como encabezados a completar en el archivo Word. Los requisitos generales del modelo solo se aplican por defecto a **Cerrado Interno**; otras modalidades requieren revisión en el Word y el circuito especial de Acotado mantiene su advertencia.
- De la tabla presupuestaria, el código PPAL y la actividad son variables registrados en la afectación (dos dígitos). **El código PPAL no es la partida de gasto 1.1**, que permanece fija en el modelo. Los demás códigos de la tabla son los del modelo de convocatoria y deben revisarse si cambiara su codificación institucional.
- Los datos de designación y de los demás documentos no se alteran.


## SDD-007 — Concurso sin aspirantes elegibles o sin inscriptos (27/10/2026)
- Regla operativa comunicada: cero inscriptos = **desierto por falta de aspirantes**; todos los aspirantes evaluados debajo de 42,50/85 = **fracasado por insuficiencia de méritos**.
- **Precisión jurídica:** el art. 45 del Anexo de Ordenanza 33/10-CS, modificado por Ordenanza 21/13-CS, emplea el término **desierto** para ambos motivos. «Fracasado» es clasificación operativa interna; antes de producir actos definitivos corresponde validar la denominación oficial.
- Las dos causas permiten sugerir **Cerrado Interno → Cerrado General → Abierto**. Abierto y Acotado no tienen una conversión inferida.
- No se deduce «sin inscriptos» de la tabla vacía: debe existir acta de inscriptos verificada y con foja. Tampoco se afirma insuficiencia hasta que todas las evaluaciones estén cargadas.
- Solo advertencia de resultado y modalidad recomendada, sin mutar Concurso ni generar una segunda convocatoria. El art. 45 prescribe acto resolutivo y nuevo llamado en no más de 30 días corridos; registrar acto/fecha y relación entre llamados queda pendiente de un circuito propio.
