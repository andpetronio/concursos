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

El naranja identifica acciones, navegación activa y foco de marca; **no** se usa de fondo general. Colores semánticos para éxito/advertencia/error no deben confundirse con branding. Los tonos complementarios se definen una vez como variables CSS (no literales repetidos).

## Contrato de componentes
- Una base privada reutilizable con barra lateral/encabezado consistentes y una base de login **sin menú privado**.
- Componentes/parciales reutilizables para: botón, campo de formulario y errores, cards, tablas, filtros, estados, avisos, modales cuando realmente se necesiten, navegación y estado vacío.
- Tokens CSS para color, tipografía, radios, espaciado, sombra y focos; clases consistentes para componentes.
- Sin CSS separado por pantalla salvo que exista una necesidad concreta y documentada. Sin estilos inline repetidos ni iconografía de estilos mezclados.
- Diseño de tablas con celdas legibles, estados accesibles, truncados conscientes y navegación por teclado.

## Criterios verificables
- Revisar como mínimo anchos de referencia de móvil (~360 px), tableta (~768 px) y escritorio (~1280 px), cuando exista navegador de pruebas. Si no, documentar la revisión pendiente.
- No hay desbordes horizontales involuntarios en pantallas básicas, el login se centra y queda separado del menú privado.
- Contraste accesible para texto y elementos interactivos; foco visible, etiquetas asociadas y errores claros.
- Los componentes deben mantener colores, padding, alturas y tipografía uniformes entre pantallas.
- Al crear una nueva pantalla, **usar antes** componentes existentes; si falta uno, crearlo de forma reutilizable.

## Control de regresiones
En cada fase con UI, el `auditor_ui` revisa consistencia visual y las variantes críticas (vacío, éxito, error, formulario inválido). No dar por validada la UI solo porque pasan los tests de backend.
