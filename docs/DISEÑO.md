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
- Revisar como mínimo anchos de referencia de móvil (~360 px), tableta (~768 px) y escritorio (~1280 px), cuando exista navegador de pruebas. Si no, documentar la revisión pendiente.
- No hay desbordes horizontales involuntarios en pantallas básicas, el login se centra y queda separado del menú privado.
- Contraste accesible para texto y elementos interactivos; foco visible, etiquetas asociadas y errores claros.
- Los componentes deben mantener colores, padding, alturas y tipografía uniformes entre pantallas.
- Al crear una nueva pantalla, **usar antes** componentes existentes; si falta uno, crearlo de forma reutilizable.
- En formularios, comprobar encabezados internos, jerarquía y espaciados; uniformidad y estados normal/error/deshabilitado de los tres tipos de campo; foco real con teclado; y flecha, padding y apertura de `select` en el navegador disponible. Documentar cualquier verificación visual imposible.

## Control de regresiones
En cada fase con UI, el `auditor_ui` revisa explícitamente este contrato —incluidos encabezados, campos y sus estados, foco con teclado, selects y reutilización— además de las variantes críticas (vacío, éxito, error, formulario inválido). Debe señalar cada incumplimiento con evidencia. No dar por validada la UI solo porque pasan los tests de backend.
