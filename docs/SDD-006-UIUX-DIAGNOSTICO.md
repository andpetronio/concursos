# SDD-006 · Diagnóstico UI/UX y plan de intervención

**Fase 1 cerrada en diagnóstico; fases 2–4 pendientes de aprobación.** Relevamiento del código y consultas agregadas de solo lectura del 24/10/2026. No se modificaron funcionalidades, modelos, migraciones, templates ni recursos. SDD-005 sigue con aceptación pendiente según `docs/ROADMAP-SDD.md`; este informe no acepta ni corrige esa entrega.

**Evidencia y límites.** Se inspeccionaron los cuatro `urls.py`, vistas, formularios, modelos relevantes, todos los templates propios, componentes, CSS y JS. El resolver del contenedor confirmó **52 patrones: 29 propios y 23 del admin**, incluidos redireccionamientos y endpoints no visuales. No existen `participantes/urls.py` ni `expedientes/urls.py`: sus rutas se incluyen en `concursos/urls.py`. No hay spec 006 en `docs/specs/`; autoriza esta fase el pedido expreso de auditoría. No se inspeccionó CoPla: su calidad es una aspiración, no evidencia comparativa. Sin verificación en navegador, capturas, generación de imágenes ni pruebas funcionales: los hallazgos son **estáticos**, no defectos visuales observados en ejecución. No se analizaron motores DOCX salvo consumidores de los campos y su interfaz.

Prioridades: **P1** consistencia transversal, integridad o confusión administrativa; **P2** productividad y legibilidad; **P3** acabado. IDs H/F/U enlazan evidencia y planificación.

## 1. Inventario completo de vistas

### Pantallas propias (20 patrones)

Prefijos: `C = /concursos/`, `K = /concursos/<int:pk>/`, `I = /concursos/configuracion-institucional/`. Las abreviaturas se concatenan literalmente; los nombres `concursos:*` pertenecen a `concursos/urls.py`, `documentos:*` a `documentos/urls.py`. Templates relativos a `templates/`. Todas las privadas comparten `layouts/private.html` (navegación, mensajes, foco y JS de formularios/sesión); login usa `layouts/auth.html`.

| Ruta · nombre | Vista Python · template | Función y componentes específicos | Hallazgo / prioridad |
|---|---|---|---|
| `/` · `dashboard` | `core.views.dashboard` · `core/dashboard.html` | Inicio; page_header, card, welcome-card, card-grid | Mensaje introductorio sin atajos de carga; escala global H2 / P2 |
| `/ingresar/` · `login` | `core.views.LoginView` · `registration/login.html` | Acceso y aviso de expiración; brand, field, button, notice | Sin ilustración; conservar independencia del menú; H2/H9 / P2 |
| `C` · `concursos:lista` | `ConcursoListView` · `concursos/lista.html` | Buscar/filtrar; lista_tabla, status, pagination, empty_state | Vacío inicial y búsqueda sin coincidencias comparten mensaje; H2/U1 / P2 |
| `Cnuevo/` · `concursos:crear` | `ConcursoCreateView` · `concursos/formulario.html` | Registrar; secciones, field, output, details, errores, concurso.js | Formulario extendido con datos documentales; F1/F4/U2 / P1 |
| `Keditar/` · `concursos:editar` | `ConcursoUpdateView` · mismo formulario | Editar datos/versionar; mismos componentes | Incluye acto oficial junto a datos previos; mantener contexto; U2/U7 / P1 |
| `K` · `concursos:detalle` | `ConcursoDetailView` · `concursos/detalle.html` | Ficha, tablas de personas, historial, checklist y documentos | Ficha larga sin índice propio; H3/H4/H6/U3 / P1 |
| `Kestado/` · `concursos:estado` | `CambioEstadoView` · `concursos/estado.html` | Cambio manual con justificación/versionado; field, form_errors | Correcta confirmación; destacar diferencia etapa/estado, U7 / P1 |
| `Kparticipantes/jurados/nuevo/` · `concursos:jurado_crear` | `participantes.views.JuradoAltaView` · `participantes/formulario.html` | Identidad, plaza, título/unidad/contacto; field/form_section_header | Identidad se introduce con resto de datos; F2/F3/U4 / P1 |
| `Kparticipantes/jurados/<int:participacion_id>/editar/` · `concursos:jurado_editar` | `JuradoEdicionView` · mismo | Editar participación, identidad solo informativa | Persona aparece en ayuda sin jerarquía; H3/F3 / P2 |
| `Kparticipantes/veedores/nuevo/` · `concursos:veedor_crear` | `VeedorAltaView` · mismo | Alta opcional APUNSJ; campos compartidos | Teléfono libre; no introducir bloqueos por ausencia; F2/F3 / P1 |
| `Kparticipantes/veedores/<int:participacion_id>/editar/` · `concursos:veedor_editar` | `VeedorEdicionView` · mismo | Contacto/cargo por participación | H3/F3; distinguir de corrección de persona / P2 |
| `Kparticipantes/aspirantes/nuevo/` · `concursos:aspirante_crear` | `AspiranteAltaView` · mismo | Identidad e inscripción; DNI y expediente compartidos | F1/F2; carga independiente del acta, sin automatismo / P1 |
| `Kparticipantes/aspirantes/<int:participacion_id>/editar/` · `concursos:aspirante_editar` | `AspiranteEdicionView` · mismo | Correo/expediente de esta inscripción | Preservar alcance por concurso y legado, F1 / P1 |
| `Kparticipantes/personas/<int:persona_id>/editar/` · `concursos:persona_editar` | `PersonaEdicionView` · mismo | Corrección compartida nombre/apellido/DNI | Aviso de impacto existente; DNI compartido protegido, F2/U4 / P1 |
| `Kcontrol-documental/<int:control_id>/historial/` · `concursos:control_historial` | `expedientes.views.HistorialControlView` · `expedientes/historial.html` | Antes/después; historial_tabla, pagination, vacío | Tabla no presenta cambios PPAL/ACTIV guardados en JSON; H7 / P1 |
| `Kcontrol-documental/etapa/historial/` · `concursos:etapa_historial` | `HistorialEtapaView` · `expedientes/historial_etapa.html` | Historial de etapas; etapa_tabla, pagination, vacío | Texto solo manual coherente hoy; deberá cambiar si se aprueba U7 / P2 |
| `I` · `documentos:configuracion` | `documentos.views.ConfiguracionView` · `documentos/configuracion.html` | Destinatario APUNSJ y accesos a Personal/membrete; field/button | Formulario principal parece toda la configuración; H1/H8 / P2 |
| `Ipersonal/` · `documentos:configuracion_personal` | `DestinatarioPersonalView` · `documentos/configuracion_personal.html` | Destinatario Personal/versionado; field/button | Navegación activa marca Concursos, no Configuración; H1 / P1 |
| `Imembrete/` · `documentos:membrete` | `MembreteInstitucionalView` · `documentos/membrete.html` | Subir PNG/JPG, vista previa/versionado | Mismo H1; estilo inline y vacío sin parcial, H8 / P2 |
| `Kdocumentos/<slug:tipo>/revisar/` · `documentos:revisar` | `GeneracionView` · `documentos/revision.html` | Fuentes, faltantes, complementos y generación; field/checkbox/details | Variantes muy distintas; F5/U5/U6, densidad y repetición / P1 |

Las vistas de concursos sin módulo indicado pertenecen a `concursos.views`; las de participantes siguientes a la primera pertenecen a `participantes.views`; las de historial a `expedientes.views`; configuración y revisión a `documentos.views`.

**Variantes documentales reales:** `documentos/registry.py` contiene **7 tipos**, no asumir seis por documentación anterior: `solicitud_jurados_rectorado` (provisional), `elecciones`, `convocatoria`, `jurados`, `apunsj` (provisional), `dictamen`, `designacion`. Comparten la ruta de revisión, no son siete URLs declaradas diferentes. La convocatoria presenta fecha de apertura; jurados recupera resolución oficial y membrete; elecciones usa Personal; dictamen/designación exigen antecedentes/complementos y mérito; designación agrega presupuesto y selección expresa de persona. Los borradores conservados se consultan en la sección de ficha: no hay pantalla independiente de historial documental ni editor DOCX web.

### Endpoints propios no visuales (9 patrones)

| Ruta · nombre | Vista · salida/función | Componentes y riesgo a preservar |
|---|---|---|
| `/salir/` · `logout` | `django.contrib.auth.views.LogoutView` · POST, redirección | Botón en navegación, CSRF; no convertir en enlace GET / P1 |
| `/sesion/actividad/` · `session_activity` | `core.views.activity` · POST, 204/401/429 | `static/js/session.js`; no renovar sin interacción / P1 |
| `/sesion/estado/` · `session_status` | `core.views.session_status` · JSON | JS de sesión, consulta sin renovación / P1 |
| `/health/` · `health` | `core.views.health` · texto | Sin UI; fuera de rediseño / P3 |
| `Kcontrol-documental/<int:control_id>/` · `concursos:control_documental` | `ControlDocumentalUpdateView` · POST, redirección a fragmento o ficha con errores | `expedientes/control_fila.html`; versiones y foco contextual / P1 |
| `Kcontrol-documental/etapa/` · `concursos:etapa_documental` | `EtapaDocumentalUpdateView` · POST, ficha/error | `expedientes/checklist.html`; permiso independiente de estado / P1 |
| `Imembrete/imagen/` · `documentos:membrete_imagen` | `ImagenMembreteView` · imagen privada | Previsualización autenticada, no confundir con ilustración decorativa / P2 |
| `Kdocumentos/archivo/<int:documento_id>/` · `documentos:descargar` | `DescargaView` · DOCX o ZIP histórico | Sección documentos; integridad, permisos y no regeneración / P1 |
| `Kdocumentos/archivo/<int:documento_id>/jurado/<int:indice>/` · `documentos:descargar_jurado` | `DescargaView` · DOCX individual conservado | Enlaces ZIP/seis notas; misma integridad / P1 |

### Administración nativa (23 patrones)

Prefijo `/admin/`, nombres `admin:*`. Vistas estándar de `AdminSite`/`ModelAdmin`, salvo login de `core.admin.ConcursosAdminSite`; adaptadas por `templates/admin/base_site.html`, `static/css/admin-adapter.css`, tokens y JS de sesión. No hay registro administrativo de concursos, personas, controles ni generaciones. Prioridad común **P2** para coherencia; **P1** para no alterar auth/permisos/sesión. Templates nativos comprobados por loader; no rediseñar ni copiar el admin entero.

| Sufijo de ruta · nombre | Vista · template principal / función | Diagnóstico estático |
|---|---|---|
| vacío · `index` | `index` · `admin/index.html`, inicio | Layout nativo distinto por diseño; adaptación de tokens existente |
| `login/` · `login` | `ConcursosAdminSite.login` · redirige al login propio o 403 | No tiene pantalla de login administrativa adicional |
| `logout/` · `logout` | `logout` · flujo nativo de salida | Conservar POST/CSRF; comprobar en fase transversal |
| `password_change/` · `password_change` | `password_change` · `registration/password_change_form.html` | Formulario nativo; medir foco/errores, no observado visualmente |
| `password_change/done/` · `password_change_done` | `password_change_done` · `registration/password_change_done.html` | Confirmación nativa |
| `autocomplete/` · `autocomplete` | `autocomplete_view` · JSON | Endpoint no visual |
| `jsi18n/` · `jsi18n` | `i18n_javascript` · catálogo JS | Endpoint no visual |
| `r/<path:content_type_id>/<path:object_id>/` · `view_on_site` | `shortcut` · redirección | Endpoint auxiliar, no pantalla propia |
| `auth/group/` · `auth_group_changelist` | `changelist_view` · `admin/change_list.html` | Lista/filtros/acciones nativos |
| `auth/group/add/` · `auth_group_add` | `add_view` · `admin/change_form.html` | Alta/permisos nativos |
| `auth/group/<path:object_id>/history/` · `auth_group_history` | `history_view` · `admin/object_history.html` | Historial nativo |
| `auth/group/<path:object_id>/delete/` · `auth_group_delete` | `delete_view` · `admin/delete_confirmation.html` | Confirmación destructiva; fuera de automatizaciones |
| `auth/group/<path:object_id>/change/` · `auth_group_change` | `change_view` · `admin/change_form.html` | Edición/permisos |
| `auth/group/<path:object_id>/` · sin nombre | `RedirectView` · redirección | Alias real, no nueva pantalla |
| `auth/user/<id>/password/` · `auth_user_password_change` | `user_change_password` · `admin/auth/user/change_password.html` | Contraseña por administrador, no mostrar datos sensibles |
| `auth/user/` · `auth_user_changelist` | `changelist_view` · `admin/change_list.html` | Lista/acciones nativas |
| `auth/user/add/` · `auth_user_add` | `add_view` · `admin/auth/user/add_form.html` | Alta/contraseña nativa |
| `auth/user/<path:object_id>/history/` · `auth_user_history` | `history_view` · `admin/object_history.html` | Historial nativo |
| `auth/user/<path:object_id>/delete/` · `auth_user_delete` | `delete_view` · `admin/delete_confirmation.html` | Confirmación nativa, no accionar en esta fase |
| `auth/user/<path:object_id>/change/` · `auth_user_change` | `change_view` · `admin/change_form.html` | Identidad/permisos nativos |
| `auth/user/<path:object_id>/` · sin nombre | `RedirectView` · redirección | Alias real |
| `^(?P<app_label>auth)/$` · `app_list` | `app_index` · `admin/app_index.html` | Índice de app auth |
| `(?P<url>.*)$` · sin nombre | `catch_all_view` · resolución/404 | Patrón residual, no vista funcional nueva |

**Estados sin ruta propia:** `core/forbidden.html` devuelve 403 desde mixin/admin; errores de campos y generales permanecen en formularios; mensajes Django en layout privado; login vencido usa `?expired=1`. No hay templates propios 404/500. Historial de estados está embebido y paginado en `K?page=…`; no inventar URL independiente. Las pantallas secundarias de control y etapa sí tienen rutas propias, inventariadas arriba.

## 2. Inconsistencias relevantes detectadas

| ID · prioridad | Evidencia estática | Intervención propuesta, no implementada |
|---|---|---|
| H1 · P1 | `components/navigation.html` solo reconoce `configuracion`; Personal y membrete cumplen la condición activa de Concursos | Resolver sección activa para las tres pantallas institucionales en un criterio compartido |
| H2 · P2 | `app.css`: h1 1,85–2,55 rem, botón primario 1,1875 rem frente a secundario 1 rem; cards hasta 2 rem y tablas con padding 0,95 rem | Escala administrativa compacta mediante tokens; medir a 1280 px antes de afirmar exceso visual. Conservar objetivos táctiles ≥44 px |
| H3 · P2 | Tablas de jurados/veedores mezclan nombre y DNI con `<br>` sin clase diferenciada; identidad de edición es `.field-help`; aspirantes sin énfasis específico | Componente identidad: apellido/nombre prioritarios, DNI/contacto secundarios; no borrar desambiguadores de homónimos |
| H4 · P2 | Las tres tablas de participantes separan acciones con `<br>`; `.actions` ya admite flex/wrap | Reutilizar grupo de acciones horizontal adaptable; distinguir editar participación de corregir persona |
| H5 · P1 | `navigation.html` no tiene disparador; a ≤760 px CSS vuelve sidebar un bloque superior completo con enlaces y salida; no hay JS de navegación | Disclosure móvil progresivo con botón, `aria-expanded`/`aria-controls`, teclado y fallback visible. No declarar sidebar inaccesible o contenido cortado sin navegador |
| H6 · P1 | Ficha serializa datos, historial, tres tablas, cinco secciones/21 controles y documentos; sin índice interno; `.status` usa el mismo estilo para todos los estados | Índice de ficha, agrupación de datos, variantes semánticas con texto. Ya hay fragmentos y estados textuales: preservarlos |
| H7 · P1 | `actualizar_control` conserva PPAL/ACTIV en antes/después; `expedientes/historial_tabla.html` solo muestra verificación/fojas/observaciones | Hacer visibles correcciones presupuestarias usando el historial existente; no inventar nuevo historial |
| H8 · P2 | `documentos/membrete.html` tiene estilo inline de previsualización; configuraciones repiten bloques de errores; algunos vacíos/documentos usan párrafos/listas locales | Clase compartida de preview, un patrón de errores y vacío; mejorar lista de generaciones sin estilos por pantalla |
| H9 · P3 | `components/brand.html` usa marca textual U y nombre Concursos Nodocentes; no existe imagen abstracta | Ilustración decorativa propia SiCon, sin logo; estrategia §4, no reemplazar marcas oficiales |
| H10 · P1 | Checklist anuncia generación «cuando esté disponible» aunque `documentos/seccion.html` ya ofrece revisión; «previa completa» no incluye todos los faltantes de `documentos.services.disponibilidad` | Copy diferenciado: preparación documental completa vs proyecto efectivamente habilitado; no prometer emisión |

**Lo que ya está resuelto y debe conservarse:** tokens oficiales correctos, login separado, skip-link, regiones de tabla desplazables/enfocables, captions, scope en encabezados, labels/errores, foco/error/deshabilitado y select compartidos, checkbox nativo táctil, salida POST, fragmentos contextuales de controles, avisos por concurrencia y texto de estados sin depender del color. No se certifican contraste, desbordes ni foco real sin prueba en navegador. Las vistas no usan CSS externo por pantalla; `concurso.js` se limita a dependencias de catálogo, `forms.js` a identificadores y `session.js` a sesión: no mezclarlos.

## 3. Componentes a reutilizar o mejorar

| Base existente | Mejora propagable | Alcance / límite |
|---|---|---|
| `static/css/tokens.css`, `app.css` | Tokens de escala tipográfica, densidad, espaciado y variantes de estados | Todas las pantallas; no CSS por URL ni reducir legibilidad/tamaño táctil |
| `templates/base.html`, `layouts/{auth,private}.html`, `components/{brand,navigation,page_header}.html` | Identidad, navegación móvil y encabezado compacto | Un solo menú; login independiente; admin mantiene adaptador |
| `components/{button,field,checkbox_field,form_errors,form_section_header}.html` | Acciones equivalentes, ayuda breve y errores uniformes | Respetar CSRF/versiones y preservar estados de campo |
| `components/{table,pagination,status,empty_state,empty_state_inline,messages}.html` | Identidad de persona, grupo de acciones, tabla compacta, semántica de avisos | Las tablas concretas extienden tabla base; `messages` hoy solo diferencia éxito del resto |
| `components/card.html`, `.card`, `.detail-list`, `.additional-data` | Resumen/agrupación e información complementaria | No convertir todos los formularios en asistentes ni ocultar errores |
| `core/fields.py`, `core/validators.py`, `core/templates/core/widgets/identificador.html`, `static/js/forms.js` | Única implementación de máscaras y límites por tipo | Frontend orienta; Django valida; excepciones históricas explícitas |
| `expedientes/presentation.py`, `catalogo.py`, parciales de checklist | Progreso, faltantes y anclas; variantes de afectación con más campos | Reutilizar catálogo de 21 requisitos y servicios; no duplicar reglas en template/JS |
| `documentos/revision.html`, `seccion.html`, `documentos/forms.py` | Resumen/faltantes agrupados, tabla/lista histórica y complementos agrupados | Siete variantes reales; sin revisar composición interna Word |

Componentes nuevos solo si falta capacidad reutilizable: identidad de persona, grupo de acciones y navegación local de ficha. Antes de extraer, usar las clases/partials anteriores; evitar abstraer un caso aislado sin beneficio.

## 4. Estrategia de identidad visual

- Conservar blanco `#FFFFFF`, superficie `#F8FAFC`, navegación blanca, naranja `#C65A17`, texto `#263342` y bordes `#E2E8F0`, conforme a `docs/DISEÑO.md`. No copiar marca, código ni recursos de CoPla.
- Planificar **una ilustración abstracta, sin logotipo**, de organización documental y recorridos administrativos: planos geométricos suaves blancos/grises y acentos naranja; sin escudos, firmas, sellos, texto incrustado ni personas identificables. No sugerir que es un acto oficial.
- Ubicación preferida: zona decorativa lateral del login en escritorio; en móvil ocultar/reducir sin desplazar credenciales. Variante recortada y discreta en bienvenida del panel solo si no demora el acceso a tareas. No en todas las fichas ni como fondo de lectura.
- Recurso decorativo con alternativa vacía, dimensiones reservadas, peso optimizado y fallback sin imagen. Aprobar composición y denominación visible «SiCon» antes de producirlo en fase 2. **No se generó imagen en esta fase.** El membrete configurable para documentos es otro recurso institucional, con finalidad y permisos diferentes.

## 5. Formularios, validaciones e históricos

### Matriz de entradas y consumidores

| ID / campo · TODAS las entradas actuales | Django / persistencia | JS / HTML / presentación | Duplicado, faltante y riesgo |
|---|---|---|---|
| F1 Expediente del concurso | `Concurso.expediente` 100; `ConcursoForm` usa `IdentificadorField(...,max_length=100)`; `validar_expediente`/`validar_cambio`; servicios `full_clean` | Widget compartido, patrón y `forms.js`; formulario y búsqueda libre (esta última no debe enmascararse) | Regla actual ya limita nuevos valores válidos a **9–12** caracteres (`2+1+1…4+1+4`), central 1–9999 sin relleno. HTML permite 100; JS no corta longitud. Aplicar máximo12 de entrada sin impedir legado intacto |
| F1 Expediente de inscripción | `Aspirante.expediente_inscripcion` 100 opcional; `AspiranteAltaForm` y `AspiranteEdicionForm` comparten campo; modelo valida cambios y edición conserva anterior | Misma máscara/widget; `participantes/formulario.html`, `aspirantes_tabla.html` | No duplicar reglas ni trasladar dato a Persona; mismo faltante de límite HTML explícito12 |
| F2 DNI | `Persona.dni` texto12 único; `PersonaDatosForm` (tres altas) y `PersonaEdicionForm` campo20; `normalizar_dni` exige 8 ASCII tras quitar puntos/espacios/guiones; `Persona.clean/save` y servicios | Widget presenta 8 como `99.999.999`; patrón acepta puntos u 8 dígitos; JS valida máscara, cursor/borrado/pegado, **sin corte máximo**. Tablas/ficha/revisión muestran DNI crudo | Máximo visual10 pendiente; no reducir columna ni rechazar separadores admitidos en servidor. Regex JS/Django son defensa complementaria, deben probar misma política. Proteger ceros y corrección compartida |
| F3 Teléfonos de Jurado y Veedor | Dos columnas40 opcionales; altas `JuradoAltaForm`/`VeedorAltaForm` CharField40; ediciones ModelForm40. `TelefonoInput` solo type=tel; no normalizador/patrón administrativo | Sin máscara ni manejador JS; visibles en `jurados_tabla.html` y `veedores_tabla.html`; aspirantes no tienen teléfono | Faltan máscara `999-9999999`, máximo11 y validación de servidor. Establecer normalización y conservación histórica antes de restringir. No convertir en number ni completar números |
| F4 Código del cargo | `Concurso.codigo_presupuestario`100; `ConcursoForm` deriva campo100; servicios full_clean sin regla5 | `concursos/formulario.html`, lista_tabla, datos dinámicos de ficha/revisión | Máximo5 ausente en ambos niveles. No inferir solo dígitos ni unicidad; preservar históricos |
| F4 PPAL y ACTIV de afectación | `ControlDocumental.partida_principal` y `actividad_presupuestaria`2; form y `clean` llaman **mismo** `normalizar_codigo_dos_digitos`; servicio full_clean | HTML maxlength2/inputmode; `control_fila.html`; sin JS de máscara propia | Ya más estrictos que5: 1→01, solo ASCII y solo afectación. No ampliarlos a5 por regla genérica; duplicación de invocación intencional a una función, no dos normalizadores |
| F5 Presupuesto complementario de designación | `GeneracionForm` crea **21** `presupuesto_*`, CharField200, sin regla5. Servicio revalida con el formulario; snapshot JSON, no columnas individuales | `revision.html` renderiza campos dinámicos; sin JS específico ni máscara | No aplicar5 indiscriminadamente a texto descriptivo. Separar códigos vs denominaciones/ejercicio/partida/caracter; aprobar alcance. `presupuesto_numero_cargo` puede repetir código del concurso: revisar consistencia sin alterar snapshot |

**Mapa completo de consumidores/auxiliares:** `concursos/views.py` busca por expediente/código y advierte duplicados; `participantes/services.py` vincula por DNI y protege cambios compartidos; `templates/concursos/{detalle,estado,lista,lista_tabla,formulario}.html`, historiales de expedientes y `templates/participantes/{formulario,jurados_tabla,veedores_tabla,aspirantes_tabla}.html` presentan los datos. El widget único contiene el único botón «Agregar guion»; `core/fields.py` contiene su ayuda y `forms.js` su activación; `.mask-separator` está en `app.css`. Eliminarlos **después**, conjuntamente; `docs/DISEÑO.md` todavía los exige y debe actualizarse con la nueva decisión.

`documentos/services.py` (`instantanea_concurso`, `fuentes_actuales`) fotografía expediente/código, DNI de jurados/aspirantes, expedientes de inscripción y PPAL/ACTIV; los complementos de designación se conservan en la generación. `GeneracionDocumento.instantanea` y `CambioControlDocumental.anterior/nuevo` son históricos, no entradas editables. `templates/documentos/revision.html` presenta expediente, DNI de fuentes y complementos. `documentos/renderers.py` solo consume estos valores; hay formateo DNI en `persona_texto` y `jurado_presentado` (criterios levemente distintos), más usos de expediente/código/presupuesto; armonizar presentación solo si se aprueba sin regenerar bytes históricos. `documentos/convocatoria_textos.py:PRESUPUESTO_FIJO` contiene códigos/textos de plantilla: no son campos de usuario ni deben recortarse. Configuración APUNSJ/Personal y membrete no tienen DNI, teléfono ni expediente/código propios. Las migraciones conservan anchos históricos; las pruebas existentes contienen casos sintéticos, no son entradas adicionales. No hay otros formularios auxiliares para estos cuatro tipos.

Los 21 sufijos reales de presupuesto son: `unidad`, `unidad_cargo`, `ejercicio`, `grupo`, `ppal`, `subppal`, `subsubppal`, `fte`, `prog`, `sprog`, `proy`, `activ`, `obra`, `finalidad`, `funcion`, `planta`, `inciso`, `partida`, `caracter`, `escalafon`, `numero_cargo` (`documentos/forms.py:PRESUPUESTO`).

### Comprobación histórica real (solo agregados)

Docker Compose existente: servicios `db` y `web` activos; PostgreSQL17, esquema public. Se consultó `information_schema.columns` y `django_migrations` **antes** de usar campos: presentes concursos0001–0007, participantes0001–0003, expedientes0001–0005 y documentos0001–0003. El esquema sí contiene campos nuevos; no se migró ni se reconstruyó/inició servicio alguno. Transacciones `BEGIN READ ONLY`/`ROLLBACK`, sin IDs, valores personales ni lectura de bytes DOCX.

| Fuente/campo | Total / no vacíos | Longitud no vacía mín.–máx. | Exceden límite propuesto | Formato propuesto |
|---|---:|---:|---:|---|
| Concurso.expediente | 1 / 1 | 9–9 | 0 | 0 fuera de patrón |
| Aspirante.expediente_inscripcion | 2 / 2 | 9–9 | 0 | 0 fuera de patrón |
| Concurso.codigo_presupuestario | 1 / 1 | 5–5 | 0 | No se inventó patrón numérico |
| Persona.dni | 8 / 8 | 8–8 almacenado | 0 crudos y 0 al presentar con puntos | 8 presentables con10; 0 fuera de 8 dígitos |
| Jurado.telefono | 6 / 6 | 1–1 | 0 crudos y 0 de longitud calculada con separador | **6 fuera de máscara**: no truncar ni convertir automáticamente |
| Veedor.telefono | 0 / 0 | No aplica | 0 sobre conjunto vacío | Sin datos para evaluar compatibilidad |
| Control.PPAL / ACTIV (cada campo) | 21 / 1 | 2–2 | 0 | No ampliar actual regla2 |

Se recorrieron recursivamente **4** instantáneas documentales y los JSON antes/después de correcciones documentales: expediente4, código4, DNI24, PPAL104 y ACTIV104 ocurrencias en generaciones (solo8 no vacías por cada código); PPAL/ACTIV tienen una ocurrencia anterior vacía y una nueva no vacía en historial. **0 excesos** en las claves encontradas, incluidos DNI con separadores de presentación. No se encontraron claves `presupuesto_*`, teléfonos ni expedientes de inscripción en ese conjunto JSON: no equivale a validar generaciones futuras de designación. Las ocurrencias JSON no son personas/registros únicos; no sumarlas a las tablas maestras. No se inspeccionaron identificadores embebidos en texto libre, archivos o sistemas externos; el resultado solo cubre la base local consultada y ese momento.

**Consulta reproducible de longitudes/formato para futuras bases** (ejecutar solo tras comprobar columnas; no muestra valores):

```sql
BEGIN READ ONLY;
WITH datos(campo, valor, limite) AS (
  SELECT 'concurso.expediente', expediente, 12 FROM concursos_concurso UNION ALL
  SELECT 'aspirante.expediente', expediente_inscripcion, 12 FROM participantes_aspirante UNION ALL
  SELECT 'persona.dni', dni, 10 FROM participantes_persona UNION ALL
  SELECT 'jurado.telefono', telefono, 11 FROM participantes_jurado UNION ALL
  SELECT 'veedor.telefono', telefono, 11 FROM participantes_veedor UNION ALL
  SELECT 'concurso.codigo', codigo_presupuestario, 5 FROM concursos_concurso UNION ALL
  SELECT 'control.ppal', partida_principal, 5 FROM expedientes_controldocumental UNION ALL
  SELECT 'control.activ', actividad_presupuestaria, 5 FROM expedientes_controldocumental
)
SELECT campo, count(*) total, count(*) FILTER (WHERE valor <> '') cargados,
       min(length(valor)) FILTER (WHERE valor <> '') min_long, max(length(valor)) max_long,
       count(*) FILTER (WHERE length(valor) > limite) excede_literal,
       count(*) FILTER (WHERE campo LIKE '%.dni' AND
         length(regexp_replace(valor, '[^0-9]', '', 'g')) + 2 > 10 OR
         campo LIKE '%.telefono' AND
         length(regexp_replace(valor, '[^0-9]', '', 'g')) + 1 > 11) excede_display,
       count(*) FILTER (WHERE valor <> '' AND CASE
         WHEN campo LIKE '%.expediente' THEN valor !~ '^[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}$'
         WHEN campo LIKE '%.dni' THEN valor !~ '^[0-9]{8}$'
         WHEN campo LIKE '%.telefono' THEN valor !~ '^[0-9]{3}-[0-9]{7}$'
         ELSE false END) fuera_formato
FROM datos GROUP BY campo ORDER BY campo;
ROLLBACK;
```

Para repetir el control JSON sin revelar contenido:

```sql
BEGIN READ ONLY;
WITH RECURSIVE arbol(origen, clave, valor) AS (
 SELECT 'generacion'::text, ''::text, instantanea FROM documentos_generaciondocumento
 UNION ALL SELECT 'anterior', '', anterior FROM expedientes_cambiocontroldocumental
 UNION ALL SELECT 'nuevo', '', nuevo FROM expedientes_cambiocontroldocumental
 UNION ALL
 SELECT a.origen, h.key, h.value FROM arbol a CROSS JOIN LATERAL (
   SELECT key, value FROM jsonb_each(CASE WHEN jsonb_typeof(a.valor)='object'
     THEN a.valor ELSE '{}'::jsonb END)
   UNION ALL
   SELECT a.clave, value FROM jsonb_array_elements(CASE WHEN jsonb_typeof(a.valor)='array'
     THEN a.valor ELSE '[]'::jsonb END)
 ) h
), datos AS (
 SELECT origen, clave, valor#>>'{}' texto,
   CASE WHEN clave='dni' THEN 10 WHEN clave='telefono' THEN 11
     WHEN clave LIKE 'expediente%' THEN 12 ELSE 5 END limite
 FROM arbol WHERE jsonb_typeof(valor)='string' AND
   (clave IN ('dni','telefono','expediente','expediente_inscripcion','codigo_presupuestario',
     'partida_principal','actividad_presupuestaria') OR clave LIKE 'presupuesto_%')
)
SELECT origen, clave, count(*) ocurrencias,
 count(*) FILTER (WHERE texto <> '') cargados, max(length(texto)) max_long,
 count(*) FILTER (WHERE length(texto)>limite) excede_literal,
 count(*) FILTER (WHERE clave='dni' AND
   length(regexp_replace(texto,'[^0-9]','','g'))+2>10 OR clave='telefono' AND
   length(regexp_replace(texto,'[^0-9]','','g'))+1>11) excede_display
FROM datos GROUP BY origen, clave ORDER BY origen, clave;
ROLLBACK;
```

Un exceso en `presupuesto_*` requiere clasificación funcional, no demuestra por sí mismo un error. Las consultas no inspeccionan ni reescriben bytes históricos. Cualquier endurecimiento debe volver a consultar antes de aplicarse; conservar valores fuera de formato al editar otros datos y exigir política nueva solo a altas/correcciones autorizadas, sin truncado silencioso.

## 6. Propuestas UX priorizadas

| ID · prioridad | Recorrido / problema sustentado | Propuesta | Tipo |
|---|---|---|---|
| U1 · P2 | Listado confunde vacío de base y sin resultados | Mensaje contextual, limpiar filtros y CTA de alta solo con permiso | Visual/copy |
| U2 · P1 | Alta/edición ahora tiene 28 datos editables, incluidos antecedentes y acto oficial | Agrupar identificación/cargo vs antecedentes/documentos; revelar complementos sin ocultar errores; mantener guardado y validación actuales | Presentación; diferir campos obligatorios o guardado parcial sería comportamiento y necesita aprobación |
| U3 · P1 | Ficha exige recorrer bloques extensos para volver a tarea | Índice de secciones, accesos a jurados/control/documentos y resumen compacto; conservar fragmentos al guardar/paginar | Navegación visual; separar rutas o paginar participantes sería comportamiento |
| U4 · P2 | Altas reingresan identidad; conflicto de DNI solo se detecta al validar; corrección afecta varios concursos | Primero mejorar encabezado/aviso y acciones; evaluar luego búsqueda explícita por DNI antes de cargar datos, con permisos y sin exponer personas por endpoint público | Visual primero; consulta/reutilización asistida en fase4, sin nueva integración CoPla |
| U5 · P1 | Checklist y generación muestran habilitaciones de diferente alcance; textos obsoletos H10 | Un resumen que separe cinco controles, jurados/datos y requisitos específicos del documento; enlazar faltantes al lugar donde se corrigen | Visual/copy usando servicios actuales; no nueva regla |
| U6 · P2 | Dictamen/designación usan orden de mérito `puesto | ID`; formulario largo y 21 complementos presupuestarios; historial de generaciones muestra últimas20 sin navegación | Agrupar complementos y destacar persona; evaluar selector/filas de mérito validadas por servidor y consulta histórica paginada | Agrupación visual; nuevo ingreso estructurado/historial paginado en fase4, sin modificar bytes previos |
| U7 · P1 | Avance Preparación→Convocatoria solicitado no coincide con reglas manuales actuales | Propuesta segura abajo; NO pasar a Convocado por checks | Comportamiento: aprobación explícita fase4 |

### Preparación → Convocatoria: separación obligatoria

| Concepto | Código actual y significado | No implica |
|---|---|---|
| Etapa documental `convocatoria` | `SeguimientoDocumental.etapa`, catálogo `SECCIONES`; `actualizar_etapa` manual, permiso documental, versión y bitácora | Estado Convocado, emisión o vencimiento |
| Estado administrativo `convocado` | `EstadoConcurso`, `concursos.services.cambiar_estado`, `CambioEstado`; elección manual autorizada | Checklist completo ni generación |
| Habilitación de proyecto | `expedientes.services.habilitacion_convocatoria`: 5 controles completos (4 fojas), 6 plazas de jurado con identidad/título/unidad y datos generales válidos; `documentos.services.disponibilidad` añade fuente y datos específicos/PPAL/ACTIV/antecedentes | Los cinco checks solos NO son toda la habilitación; tampoco prueban emisión |
| Acto oficial emitido | Ya existe `Concurso.resolucion_convocatoria` (número con formato, requerido para notas a jurados); registro separado del borrador | El número no es una firma digital, ni se deduce de generar/publicar/checkear |

**Candidato a aprobar:** avanzar únicamente la **etapa documental** desde `preparacion` a `convocatoria` cuando los cinco controles estén realmente completos, sin modificar estado administrativo, emisión, controles futuros ni requisitos de generación. Mostrar «Documentación previa completa; completar datos/jurados para preparar el proyecto» si la habilitación integral aún falla. No ejecutar en GET, renderizado, descarga, polling o JavaScript.

Implementación futura acotada al servicio transaccional que registra el último requisito: bloquear seguimiento y controles pertinentes en orden estable, comprobar nuevamente completitud y etapa inicial, comprobar permiso documental, incrementar versión y crear una sola entrada de historial con autor/fecha/origen automático. Repetir guardado no crea otra transición; etapa posterior nunca retrocede por desmarcar, ni estado avanza. Una desverificación posterior muestra faltantes y bloquea generación si corresponde. Concurrencia entre operadores debe producir un solo evento, no dos. Dado que hoy `actualizar_control` bloquea solo el control, la nueva coordinación requiere diseño de locks y prueba específica, no añadir una llamada ingenua fuera de transacción.

**Decisiones todavía abiertas:** usar cinco controles o habilitación integral como disparador; distinguir origen automático en bitácora sin falsear usuario; corrección manual de vuelta a Preparación (hoy permitida) y prevención de reavance no deseado; no aplicar a históricos sin acción/confirmación específica. El candidato no puede reavanzar después de una corrección manual intencional sin política aprobada. El estado Convocado debe continuar separado: si se desea sugerirlo al registrar acto oficial, diseñar confirmación y permiso de estado, nunca deducir emisión de cinco checks o publicación. Hoy solo existe sugerencia de Con dictamen, no de Convocado.

## 7. Plan concreto de fases 2, 3 y 4

Orden: **sistema compartido → adopción total → comportamiento aprobado**. Una entrega por aprobación; no ejecutar el plan como autorización implícita.

| Fase | Archivos/módulos y componentes | Dependencias / riesgos | Pruebas necesarias y aceptación |
|---|---|---|---|
| **2 · Fundaciones visuales** | `docs/DISEÑO.md`, `static/css/{tokens,app,admin-adapter}.css`, `templates/{base,layouts/auth,layouts/private}.html`, `components/{brand,navigation,page_header,button,table,status,messages}.html`; nuevo recurso decorativo y JS de navegación solo si necesarios | Aprobación identidad/densidad; no mezclar timeout con menú ni crear CSS por vista; progresivo sin JS. Corregir sección activa H1 con alcance común | Navegador360/768/1280, teclado/lectura, zoom/foco/contraste, menú cerrado/abierto y sin JS; login sin navegación privada; POST logout y expiración1800s intactos. Tokens únicos, navegación institucional correcta, escala coherente y sin desbordes involuntarios |
| **3 · Adopción y entradas** | Todos los templates de §§1–3, parciales de concursos/participantes/expedientes/documentos, widgets; `core/{fields,validators}.py`, `static/js/forms.js`, formularios/modelos/servicios de concursos/participantes según validación compartida; `documentos/forms.py` para códigos aprobados, `expedientes/historial_tabla.html`; tests existentes por app | Requiere fase2 y decisiones F3/F5/legado; no reducir columnas ni tocar migraciones anteriores. Quitar ayuda/botón guion en conjunto con contrato. Evitar que maxlength impida conservar histórico; no enmascarar búsquedas. PPAL/ACTIV siguen2 | Matriz de **20 pantallas**, 7 variantes de revisión, admin y9 endpoints; vacío/error/éxito/solo consulta/sin permiso. Pruebas límite expediente9/12/13 y central1/4/5; DNI8 dígitos/10 visuales, pegado/cursor/ceros; teléfono10 dígitos/11 visuales y fuera de formato; código5/6. Servidor sin JS y entradas forjadas; legado intacto, unicidad/persona y versiones. `manage.py check`, migraciones dry-run y suite pertinente en BD de pruebas. Ningún truncado, sin CSS por vista, nombres prioritarios/acciones alineadas y H7 visible |
| **4 · UX funcional y validación transversal** | `expedientes/{services,models,forms,presentation}.py` y migración aditiva **solo si aprobada** para origen/política de avance; `concursos/{services,views}.py` solo si se aprueba sugerencia separada; UX de participantes y `documentos/{forms,views,services}.py` y templates según U4/U6 aprobado; pruebas de concurrencia y recorrido | Requiere fase3 y decisiones funcionales expresas; compatibilidad de historial/rollback manual, locks y permisos; no automatizar emisión/ganador/notificación ni reabrir alcance SDD005 | Integración alta→participantes→21 controles→revisión→descarga→estado/historial. Doble envío, concurrentes, no-op, desverificación, etapa adelantada/corrección manual, permisos separados y sesión expirada. Un solo evento auditable; ningún retroceso/Convocado automático; bytes/snapshots históricos intactos; revisión administrativa y UI360/768/1280 |

**Cobertura transversal requerida:** `core/tests/{test_identificadores,test_auth,test_concurrency}.py`; pruebas de concursos/participantes/expedientes existentes (`test_ajustes`, `test_concursos`, `test_participantes`, `test_documental`, `test_concurrency`, según app); `documentos/tests.py`. No ejecutar pruebas sobre datos reales. Revisores independientes de Django/UI/seguridad al implementar según alcance; no se lanzaron auditorías duplicadas en esta fase documental.

**Verificación efectuada en fase1:** lectura estática dirigida; resolver Django del contenedor existente (52 patrones); loader de10 templates admin; introspección de esquema/migraciones; agregados SQL de tablas y JSON en transacción de solo lectura; comparación de hashes inicial/final de archivos para aislar esta entrega; `git diff --check`. No se corrió suite, `manage.py check`, `makemigrations`, servidor nuevo ni auditoría visual: no hay código implementado que certificar en esta fase. El fallo inicial de acceso al socket Docker se resolvió con permiso de herramienta y solo lecturas, no cambiando el entorno.

## 8. Decisiones funcionales que requieren aprobación

| Decisión | Recomendación / tradeoff | Bloquea |
|---|---|---|
| D1 Identidad y densidad | Ilustración abstracta en login, discreta en panel; mantener marca oficial separada. Densidad administrativa común sin sacrificar 44px; medir antes de fijar tamaños | Fase2, no generación de imagen en fase1 |
| D2 Teléfonos y legado | Nueva máscara nacional fija solicitada; conservar6 valores históricos fuera de formato sin cambios, exigir corrección explícita al editarlos. Rechazar o soportar internacionales/internos requiere decisión; no inventar prefijo ni rellenar | Fase3 F3 |
| D3 Alcance códigos5 | Aplicar5 al código de cargo; mantener PPAL/ACTIV2. Clasificar cada complemento `presupuesto_*` como código o descripción antes de endurecer; evita bloquear texto administrativo válido | Fase3 F4/F5 |
| D4 Longitud visible vs normalización | Máximos visuales expediente12 y DNI10, sin reducir almacenamiento ni perder compatibilidad con normalizador actual y legados. Probar pegados admitidos; no cortar cadenas silenciosamente | Fase3 F1/F2 |
| D5 Disparador de avance | Preferencia a decidir: cinco controles completos para **etapa**, con habilitación integral informada aparte; usar habilitación integral evita avance prematuro pero demora visibilidad de Convocatoria | Fase4 U7 |
| D6 Control de automatismo | Aprobar historial/origen, no retroceso, tratamiento de corrección manual y no aplicación masiva a históricos. Sustituye solo la decisión vigente de etapa manual; **no** la de estado manual | Fase4 U7 |
| D7 Acto oficial / estado | Mantener registro de resolución oficial y cambio manual separado; eventual sugerencia de Convocado necesita confirmación. Definir evidencia/fecha si se requiere, sin inventar dato desde checklist | Solo mejora funcional fase4, no condiciona rediseño |
| D8 UX de datos y documentos | Aprobar alcance de búsqueda asistida de persona, mérito estructurado, retorno a revisión y paginación histórica. Beneficio operativo vs mayor lógica/permisos/pruebas; no incluirlos automáticamente por ser convenientes | Fase4 U4/U6 |

**Siguiente paso:** revisar estas decisiones y autorizar únicamente fase2. Ninguna fase posterior comenzó; los hallazgos sobre interfaz SDD-005 quedan documentados, no corregidos ni aceptados aquí.
