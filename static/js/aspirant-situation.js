/* Mostrar solo las opciones pertinentes al registrar una actuación de aspirante.
 * La validación y la autoridad documental siguen definidas en el servidor.
 */
(() => {
  "use strict";
  const formulario = document.querySelector("[data-situation-action-form]");
  if (!formulario) return;

  const actuacion = formulario.querySelector('select[name="tipo"]');
  const motivos = formulario.querySelector("[data-exclusion-motive]");
  const radios = motivos ? [...motivos.querySelectorAll('input[name="motivo_exclusion"]')] : [];
  const fecha = formulario.querySelector("[data-action-date]");
  const detalles = formulario.querySelector("[data-action-details]");
  const clase = formulario.querySelector('select[name="clase_documento"]');
  const ayudaDocumento = formulario.querySelector("[data-document-type] .field-help");
  const guia = formulario.querySelector("[data-action-guide]");
  const consecuencias = formulario.querySelector("[data-action-consequences]");
  const consecuenciaTexto = formulario.querySelector("[data-action-consequence-text]");
  const boton = formulario.querySelector("[data-action-submit]");
  if (!actuacion || !fecha || !detalles || !clase || !guia || !boton) return;

  const orientaciones = {
    impugnacion: "Registrá la presentación recibida. Una impugnación en trámite no excluye al aspirante.",
    exclusion: "Seleccioná primero el motivo. SiCon indicará el respaldo documental correspondiente.",
    desistimiento: "Registrá el desistimiento que conste en el expediente y su documento respaldatorio.",
    rectificacion: "Registrá la actuación formal que deja sin efecto la situación vigente.",
  };
  const indicacionesDocumento = {
    impugnacion: "Identificá la presentación de impugnación que consta en el expediente.",
    desistimiento: "Identificá el documento en el que consta el desistimiento.",
    rectificacion: "Indicá la actuación formal que respalda el cierre o la rectificación.",
  };
  const efectos = {
    impugnacion: "La impugnación queda en trámite, sin excluir al aspirante del mérito. Los antecedentes permanecen registrados.",
    exclusion: "La exclusión impide continuar en la oposición y en el orden de mérito. Los puntajes históricos se conservan.",
    desistimiento: "El desistimiento impide continuar en la oposición y en el orden de mérito. El historial permanece disponible.",
    rectificacion: "Se restablece la situación de inscripto y se conserva el historial de actuaciones previas.",
  };
  let tipoAnterior = null;

  function actualizar() {
    const tipo = actuacion.value;
    const esExclusion = tipo === "exclusion";
    if (tipoAnterior !== null && tipoAnterior !== tipo) {
      // No reutilizar una causa o un respaldo que pertenecían a otra actuación.
      radios.forEach((radio) => { radio.checked = false; });
      clase.value = "";
      ["fecha_decision", "documento", "fojas", "fundamento", "constancia_comunicacion"].forEach((nombre) => {
        const campo = formulario.elements.namedItem(nombre);
        if (campo) campo.value = "";
      });
    }
    tipoAnterior = tipo;
    // No pedir respaldo ni fecha hasta conocer el motivo de una exclusión.
    const motivo = radios.find((radio) => radio.checked)?.value || "";
    const pasoCompleto = Boolean(tipo) && (!esExclusion || Boolean(motivo));
    if (motivos) motivos.hidden = !esExclusion;
    fecha.hidden = !pasoCompleto;
    detalles.hidden = !pasoCompleto;
    if (consecuencias) consecuencias.hidden = !pasoCompleto;
    boton.disabled = !pasoCompleto;
    guia.textContent = orientaciones[tipo] || "Elegí la actuación acreditada para ver los datos que corresponde completar.";
    if (consecuenciaTexto && tipo) consecuenciaTexto.textContent = efectos[tipo];
    if (ayudaDocumento) {
      ayudaDocumento.textContent = esExclusion
        ? (motivo === "requisitos"
          ? "Respaldo exigido: acta del Jurado."
          : motivo === "impugnacion_aceptada" ? "Respaldo exigido: resolución rectoral." : "Primero seleccioná el motivo.")
        : (indicacionesDocumento[tipo] || "Seleccioná el documento que consta en el expediente.");
    }

    // Una exclusión tiene un único tipo de respaldo admisible según la causa.
    // No se genera un documento ni se presupone que la actuación haya ocurrido.
    const esperado = esExclusion
      ? (motivo === "requisitos" ? "acta" : motivo === "impugnacion_aceptada" ? "resolucion" : "")
      : null;
    for (const opcion of clase.options) {
      const noCorresponde = esExclusion && Boolean(opcion.value) && opcion.value !== esperado;
      opcion.hidden = noCorresponde;
      opcion.disabled = noCorresponde;
    }
    if (esExclusion) clase.value = esperado;
  }

  actuacion.addEventListener("change", actualizar);
  radios.forEach((radio) => radio.addEventListener("change", actualizar));
  actualizar();
})();
