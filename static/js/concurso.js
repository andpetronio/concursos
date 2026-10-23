/* Dependencias del formulario de concurso. La matriz se resuelve en Python. */
(() => {
  "use strict";
  const form = document.querySelector("[data-concurso-form]");
  if (!form) return;
  const catalogo = JSON.parse(document.getElementById("catalogo-cargos").textContent);
  const agrupamiento = form.elements.agrupamiento;
  const categoria = form.elements.categoria;
  const tramo = document.getElementById("tramo-calculado");
  const modalidad = form.elements.modalidad;
  const referencia = document.getElementById("referencia-acotado");
  const opciones = () => catalogo[agrupamiento.value] || [];
  const actualizarTramo = () => {
    const elegida = opciones().find(item => item.categoria === categoria.value);
    tramo.textContent = elegida ? elegida.tramo : "Seleccioná agrupamiento y categoría";
  };
  const actualizarCategorias = () => {
    const anterior = categoria.value;
    categoria.replaceChildren(new Option("Seleccioná una categoría", ""));
    for (const item of opciones()) categoria.add(new Option(item.categoria, item.categoria));
    categoria.value = opciones().some(item => item.categoria === anterior) ? anterior : "";
    categoria.disabled = !agrupamiento.value;
    actualizarTramo();
  };
  const actualizarModalidad = () => { referencia.hidden = modalidad.value !== "acotado"; };
  agrupamiento.addEventListener("change", actualizarCategorias);
  categoria.addEventListener("change", actualizarTramo);
  modalidad.addEventListener("change", actualizarModalidad);
  // El HTML ofrece un fallback usable sin JS; al iniciar se filtra conservando
  // cualquier selección válida. Los errores enviados por Django permanecen.
  actualizarCategorias();
  actualizarModalidad();
})();
