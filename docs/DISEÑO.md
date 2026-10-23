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

## Criterios verificables
- Revisar como mínimo anchos de referencia de móvil (~360 px), tableta (~768 px) y escritorio (~1280 px), cuando exista navegador de pruebas. Si no, documentar la revisión pendiente.
- No hay desbordes horizontales involuntarios en pantallas básicas, el login se centra y queda separado del menú privado.
- Contraste accesible para texto y elementos interactivos; foco visible, etiquetas asociadas y errores claros.
- Los componentes deben mantener colores, padding, alturas y tipografía uniformes entre pantallas.
- Al crear una nueva pantalla, **usar antes** componentes existentes; si falta uno, crearlo de forma reutilizable.
- En formularios, comprobar encabezados internos, jerarquía y espaciados; uniformidad y estados normal/error/deshabilitado de los tres tipos de campo; foco real con teclado; y flecha, padding y apertura de `select` en el navegador disponible. Documentar cualquier verificación visual imposible.

## Control de regresiones
En cada fase con UI, el `auditor_ui` revisa explícitamente este contrato —incluidos encabezados, campos y sus estados, foco con teclado, selects y reutilización— además de las variantes críticas (vacío, éxito, error, formulario inválido). Debe señalar cada incumplimiento con evidencia. No dar por validada la UI solo porque pasan los tests de backend.
