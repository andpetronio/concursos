/* F4F: ubicacion del menu de aspirantes fuera del recorte de la tabla. */
(() => {
  "use strict";
  const menus = document.querySelectorAll(".aspirant-menu-links[popover]");
  if (!menus.length) return;

  const margen = 8;
  const separacion = 6;
  const disparador = (menu) => document.getElementById(`aspirant-menu-trigger-${menu.id.slice("aspirant-menu-".length)}`);

  const ubicar = (menu) => {
    const boton = disparador(menu);
    if (!boton) return;
    const rect = boton.getBoundingClientRect();
    const cuadro = menu.getBoundingClientRect();
    const izquierda = Math.max(margen, Math.min(rect.right - cuadro.width, window.innerWidth - cuadro.width - margen));
    const espacioAbajo = window.innerHeight - rect.bottom - separacion;
    const espacioArriba = rect.top - separacion;
    const abrirArriba = cuadro.height > espacioAbajo && espacioArriba > espacioAbajo;
    const propuesta = abrirArriba ? rect.top - cuadro.height - separacion : rect.bottom + separacion;
    const arriba = Math.max(margen, Math.min(propuesta, window.innerHeight - cuadro.height - margen));
    menu.style.left = `${Math.round(izquierda)}px`;
    menu.style.top = `${Math.round(arriba)}px`;
  };

  menus.forEach((menu) => {
    menu.addEventListener("beforetoggle", (evento) => {
      if (evento.newState !== "open") return;
      // Posicion inicial junto al boton, antes de medir el alto exacto.
      const boton = disparador(menu);
      if (!boton) return;
      const rect = boton.getBoundingClientRect();
      const ancho = Math.min(272, window.innerWidth - 2 * margen);
      menu.style.left = `${Math.max(margen, rect.right - ancho)}px`;
      menu.style.top = `${Math.max(margen, rect.bottom + separacion)}px`;
    });
    menu.addEventListener("toggle", (evento) => {
      if (evento.newState === "open") ubicar(menu);
    });
  });

  const reubicarAbiertos = () => menus.forEach((menu) => {
    if (menu.matches(":popover-open")) ubicar(menu);
  });
  window.addEventListener("resize", reubicarAbiertos);
  document.addEventListener("scroll", reubicarAbiertos, true);
})();
