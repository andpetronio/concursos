# Sistema de diseño: Blanco y naranja — decisión crítica

## Tokens oficiales (única fuente)
| Uso | Color |
|---|---|
| Fondo global | `#FFFFFF` |
| Superficie / tarjetas | `#F8FAFC` |
| Navegación | `#FFFFFF` |
| Primario de acción | `#C65A17` |
| Texto principal | `#263342` |
| Bordes | `#E2E8F0` |

El naranja identifica acciones, navegación activa y foco de marca; **no** se usa de fondo general. Colores semánticos para éxito/advertencia/error no deben confundirse con branding. Los tonos complementarios se definen una vez como variables CSS (no literales repetidos). El borde de campos (`#D9E0E8`) es un token específico y no reemplaza el borde general.

## Contrato de componentes
- Una base privada reutilizable con barra lateral/encabezado consistentes y una base de login **sin menú privado**.
- Componentes/parciales reutilizables para: botón, campo de formulario y errores, cards, tablas, filtros, estados, avisos, modales cuando realmente se necesiten, navegación y estado vacío.
- Tokens CSS para color, tipografía, radios, espaciado, sombra y focos; clases consistentes para componentes.
- Sin CSS separado por pantalla salvo que exista una necesidad concreta y documentada. Sin estilos inline repetidos ni iconografía de estilos mezclados.
- Diseño de tablas con celdas legibles, estados accesibles, truncados conscientes y navegación por teclado.

### Densidad y navegación (SDD-006 · 2A)
- Escala administrativa compartida: título `clamp(1.65rem, 2vw, 2rem)`, secciones `1.125rem`, cuerpo, botones, navegación y tablas `1rem` (16px), interlineado base `1.45`; ayudas/cabeceras de tabla `.875rem`. La densidad reduce espacio, no legibilidad. Tokens en `tokens.css`, sin reglas por ruta.
- Los botones primarios compactos usan fondo/borde `--primary-ink` (`#93400D`), tono naranja oscuro existente, para contraste blanco ≥4.5:1; hover `--primary-deep`. El token oficial `--primary` (`#C65A17`) permanece intacto en identidad, foco y navegación activa. Los secundarios conservan fondo blanco, texto oscuro y hover suave.
- Tarjetas: padding `1–1.25rem`; contenido: `1–1.5rem`; tablas: `.5rem .75rem` por celda; secciones `1.25rem`, acciones `.75rem` y filas de detalle `.5rem` verticales, mediante tokens compartidos. Controles conservan mínimo `44px`; enlaces de tabla también en móvil. No se alteran estados de campos ni colores oficiales.
- Sidebar persistente por encima de `760px` (incluye 768px), sin botones móviles: CSS específico independiente de `.button` y `hidden` sincronizado al breakpoint. En móvil, sin JS los enlaces siguen visibles; con JS el botón «Menú» abre panel modal con cierre, Escape, foco inicial/retorno, ciclo de Tab, fondo no interactivo y scroll bloqueado. Elegir enlace cierra sin reenfocar el disparador; resize limpia el estado modal y transfiere el foco al primer enlace visible solo si desaparece el botón móvil enfocado; conserva el foco en enlaces/contenido visibles. Se recuerda el último foco significativo porque el navegador puede ocultar y desenfocar los controles antes del evento de cambio de media query.
- `navigation_section` centraliza sección activa: el prefijo canónico de Configuración institucional incluye Personal, membrete e imagen; revisión/descargas documentales pertenecen a Concursos. Se conservan permisos y logout POST/CSRF. Login no carga navegación privada ni su script.

### Secciones y formularios
- El título de cada sección va **dentro** de su contenedor, nunca sobrepuesto al borde. El encabezado compartido diferencia título, descripción y campos mediante tipografía y espaciados definidos por tokens.
- `input`, `textarea` y `select` comparten altura mínima, padding, tipografía, borde discreto `#D9E0E8` y radio cercano a `8 px`. Error y deshabilitado son estados distinguibles entre sí y del estado normal, sin perder legibilidad.
- El foco es visible y accesible: borde institucional `#C65A17` y, cuando corresponda, halo exterior sutil (referencia: `rgba(198, 90, 23, 0.12)`). Preferir `:focus-visible` sin quitar el indicador a controles que necesitan `:focus` para navegar con teclado; el error conserva su señal visual al recibir foco.
- Los `select` reservan espacio para el texto y sitúan la flecha aproximadamente a `14 px` del borde derecho. Usar la apariencia compartida donde el navegador la soporte y conservar una alternativa nativa compatible; no añadir librerías para este fin.
- Toda pantalla nueva adopta estas reglas mediante componentes y estilos compartidos. No duplicar soluciones visuales por pantalla cuando exista un componente común.

### Tipos de entrada y máscaras compartidas
- DNI: `type="text"`, `inputmode="numeric"`, visual `99.999.999`; exactamente 8 dígitos, pegado con/sin puntos y ceros iniciales preservados. Nunca usar `number` para identificadores.
- Expediente (concurso o inscripción): `type="text"`, `inputmode="numeric"`, patrón `99-NNNN-9999`. El segundo bloque es un entero 1–9999 de longitud variable, sin ceros de relleno. El guion que lo cierra se ingresa explícitamente: no inferir su longitud ni completar ceros.
- El widget de expediente ofrece «Agregar guion» como ayuda compartida para teclados numéricos sin esa tecla. Es un botón sin envío, visible con JS, con referencia al campo y devolución de foco a la posición de edición.
- Correo: `email`; teléfono: `tel`, sin máscara; fecha editable: `date` cuando se incorpore un campo de fecha. No enmascarar búsquedas de texto libre ni otros campos.
- Centralizar widgets/campos en `core/fields.py`, normalizadores y validaciones en `core/validators.py`, comportamiento progresivo en `static/js/forms.js`. Backend valida siempre, también sin JS; no agregar dependencias ni scripts por formulario.
- Mantener posición de edición y selección al escribir, borrar o pegar. Borrar junto a un punto de DNI debe permitir continuar sin quedar atrapado en el separador. No reformatear valores históricos fuera de formato al abrir la edición: solo podrán conservarse sin cambios o corregirse explícitamente.
- Información opcional complementaria puede agruparse en `details`/`summary` nativos, con estilos compartidos y foco de teclado. «Funciones del cargo» usa esta sección y queda abierta si contiene información o errores.
- Selects dependientes: conservar una selección compatible al cambiar el campo padre; limpiar los valores que dejan de ser válidos, sin elegir arbitrariamente la primera opción. El tramo de cargo se muestra en `output` con etiqueta y anuncio accesible, usando tokens de campos/superficies; no como selector ni entrada editable. La categoría sin agrupamiento está deshabilitada con JS y conserva el estilo compartido de ese estado.
- Checkboxes mediante `components/checkbox_field.html`: control nativo con acento institucional y etiqueta clicable de al menos 44 px de alto. El nombre accesible debe contener la etiqueta visible; usar contexto del requisito cuando se repite «Verificado». Mantener foco y activación con Espacio, sin widgets JavaScript propios.
- Los formularios de filas extensas incorporan un fragmento contextual en su acción POST y redirección de éxito. Los errores permanecen junto al campo con aviso accesible y el navegador aterriza en esa fila; margen de desplazamiento evita ocultarla bajo el encabezado fijo. Los estados de checklist distinguen completo, foja pendiente, pendiente exigible y no registrado de etapas futuras mediante texto, sin depender solo del color.

## Criterios verificables
- Revisar como mínimo anchos de referencia de móvil (~360 px), tableta (~768 px) y escritorio (~1280 y 1440 px), cuando exista navegador de pruebas. Si no, documentar la revisión pendiente.
- No hay desbordes horizontales involuntarios en pantallas básicas, el login se centra y queda separado del menú privado.
- Contraste accesible para texto y elementos interactivos; foco visible, etiquetas asociadas y errores claros.
- Los componentes deben mantener colores, padding, alturas y tipografía uniformes entre pantallas.
- Al crear una nueva pantalla, **usar antes** componentes existentes; si falta uno, crearlo de forma reutilizable.
- En formularios, comprobar encabezados internos, jerarquía y espaciados; uniformidad y estados normal/error/deshabilitado de los tres tipos de campo; foco real con teclado; y flecha, padding y apertura de `select` en el navegador disponible. Documentar cualquier verificación visual imposible.

## Control de regresiones
En cada fase con UI, el `auditor_ui` revisa explícitamente este contrato —incluidos encabezados, campos y sus estados, foco con teclado, selects y reutilización— además de las variantes críticas (vacío, éxito, error, formulario inválido). Debe señalar cada incumplimiento con evidencia. No dar por validada la UI solo porque pasan los tests de backend.

### Acceso, orientación y propuesta de ficha (SDD-006 · 2B)
- Acceso independiente con denominación textual **SiCon**, sin inventar una marca institucional. Dos columnas en escritorio; en móvil se prioriza el formulario. Reserva explícita para una ilustración abstracta que aportará el usuario: sin imagen generada, CSS art ni sustitución de símbolos oficiales. Campos, errores, CSRF y aviso de inactividad reutilizan los componentes existentes.
- Panel inicial orientado a tareas: consulta como acción principal y registro como secundaria, este último solo con permisos de consulta y alta. Descripción de participantes, control y borradores, sin métricas ni reglas nuevas; no hay consultas adicionales ni cambios de navegación.
- **Propuesta pendiente, no patrón aprobado:** `concursos/detalle_piloto.html` no tiene ruta de producción. Propone resumen de expediente/cargo/estado/situación/etapa, índice de secciones y acciones jerarquizadas. `summary-facts` y `section-index` son piezas reutilizables; su uso queda aislado al piloto hasta aceptación.
- La tabla piloto reutiliza `components/table.html` y un único `person_identity.html`: apellido/nombre en negrita, DNI secundario siempre visible; participación, título, unidad, cargo histórico, contactos e inscripción se conservan. Una sola composición para los tres tipos; acciones de participación/inscripción y corrección de persona separadas, con permisos originales. Las tablas productivas no cambian. Desplazamiento horizontal local accesible cuando una tabla no cabe en móvil.
- Checklist, avisos, formularios de controles, generación e historial se incluyen desde parciales reales. La propuesta no recalcula habilitaciones, oculta faltantes ni convierte controles en actos oficiales. No se propaga a otras pantallas antes de validación del usuario.

### Ficha productiva y participantes (SDD-006 · primera entrega 3A)
- La denominación del cargo es el H1; expediente en segundo nivel. Modalidad y clasificación del cargo se agrupan por separado de estado administrativo, situación y etapa documental, sin equivalencias ni deducciones. Los datos completos siguen abiertos en la ficha; en escritorio se aprovechan dos pares de etiqueta/valor por fila.
- Corrección 3A pendiente de aceptación: ocho pestañas progresivas en la ficha real. Sin JavaScript, todas las secciones y sus enlaces originales permanecen disponibles. Con JavaScript, un solo panel visible, roles/estados ARIA, foco móvil y activación manual (flechas/Home/End recorren, Enter/Espacio seleccionan). Selección con peso y subrayado, barra sticky y desplazamiento horizontal local con indicación textual cuando hay opciones fuera del área visible.
- El hash conserva el destino original, incluidos controles individuales; refresco/atrás/adelante reabren su panel sin recrear formularios. Los errores renderizados por Django tienen prioridad inicial. Los retornos de participantes añaden su fragmento; corrección de persona admite únicamente secciones conocidas donde esa persona participa, nunca URLs externas. La paginación del historial conserva querystring y añade su fragmento también sin JS. No hay AJAX ni almacenamiento de personas/selección en storage.
- Jurados, veedores y aspirantes reutilizan `person_identity`, `table`, `button`, ayuda de scroll y acciones de participación compartidas. Nombre fuerte, DNI siempre visible, datos históricos/contactos legibles en segundo nivel. Las tres tablas mantienen sus interfaces y sus permisos; no se crea una biblioteca ni una tabla condicional universal.
- `participation-actions` reutiliza botones secundarios para ambas acciones: etiquetas explícitas y borde discontinuo para corrección compartida de persona. Mantiene edición de vínculo y corrección de persona en una fila horizontal con objetivos de al menos 44 px. Hasta 760 px, las acciones se acomodan en varias líneas dentro de su columna; en pantallas estrechas el desplazamiento pertenece a la región de tabla etiquetada/enfocable, con ayuda visible de teclado; nunca a toda la página. No altera las acciones verticales del piloto ni tablas de otras vistas. La propuesta 2B continúa separada, no aprobada por esta implementación.
