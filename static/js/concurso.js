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

  // Vacancia: se priorizan los campos relevantes sin eliminar ni borrar datos existentes.
  const vacancia = form.querySelector("[data-vacancy-fields]");
  if (vacancia) {
    const causa = form.elements.causa_vacancia;
    const cese = vacancia.querySelector("[data-vacancy-cessation]");
    const acto = vacancia.querySelector("[data-vacancy-act]");
    const otra = vacancia.querySelector("[data-vacancy-other]");
    const aviso = vacancia.querySelector("[data-vacancy-stale]");
    const tituloActo = vacancia.querySelector("[data-vacancy-act-title]");
    const notaActo = vacancia.querySelector("[data-vacancy-act-note]");
    const ceseCausas = new Set(["jubilacion", "renuncia", "fallecimiento", "concurso", "efectivizacion"]);
    const tieneValor = (nombres) => nombres.some((nombre) => form.elements[nombre]?.value.trim());
    const actualizarVacancia = () => {
      const esCese = ceseCausas.has(causa.value);
      const datosAnteriores = tieneValor(["ex_titular", "resolucion_baja"]);
      cese.hidden = !(esCese || datosAnteriores);
      aviso.hidden = esCese || !datosAnteriores;
      acto.hidden = !causa.value && !tieneValor(["acto_vacancia"]);
      otra.hidden = causa.value !== "otra" && !tieneValor(["detalle_vacancia"]);
      tituloActo.textContent = ["nuevo", "traslado"].includes(causa.value) ? "Origen del cargo" : "Acto administrativo de respaldo";
      notaActo.textContent = causa.value === "nuevo"
        ? "Identificá el acto de creación del cargo, si está acreditado en el expediente."
        : causa.value === "traslado"
          ? "Indicá el acto administrativo que dispuso el traslado del cargo. Es necesario para generar la convocatoria."
          : "Consigná el acto que respalda la vacancia, si corresponde y no está identificado mediante resolución de baja.";
    };
    causa.addEventListener("change", actualizarVacancia);
    actualizarVacancia();
  }
})();
