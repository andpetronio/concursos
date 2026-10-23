---
name: ui-consistente
description: Crear o revisar templates, formularios, tablas, navegación y estilos de Concursos aplicando estrictamente identidad Blanco y naranja y componentes compartidos.
---
# Contrato visual
1. Leer `docs/DISEÑO.md` antes de tocar UI.
2. Reutilizar `base` y componentes/parciales existentes. Si falta un componente común, agregarlo en espacio compartido.
3. Respetar tokens: fondo #FFFFFF, superficies #F8FAFC, navegación #FFFFFF, naranja #C65A17, texto #263342, bordes #E2E8F0.
4. Mantener login independiente del menú privado, responsive, errores, estados vacíos, etiquetas, contraste y foco visible.
5. No crear CSS por pantalla ni colores inline dispersos sin necesidad justificada.
6. Verificar visualmente con navegador en dispositivos de referencia si está disponible; si no, reportar que falta validación visual.
7. Antes de dar por terminada cualquier funcionalidad con interfaz, comprobar el contrato de `docs/DISEÑO.md` para encabezados internos, campos y estados, foco con teclado, selects y reutilización. Corregir los incumplimientos o informar la verificación pendiente; las pruebas de backend no sustituyen esta revisión.
