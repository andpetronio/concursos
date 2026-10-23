/* Máscaras progresivas compartidas. Django sigue validando cada envío. */
(() => {
  "use strict";
  const digits = (value) => value.replace(/[^0-9]/g, "");
  const formatDni = (value) => {
    const raw = digits(value);
    return raw.slice(0, 2) + (raw.length > 2 ? "." + raw.slice(2, 5) : "") +
      (raw.length > 5 ? "." + raw.slice(5) : "");
  };
  const formatExpediente = (value) => {
    const raw = value.replace(/[^0-9-]/g, "");
    // El usuario cierra el bloque central con guion: no se adivina su longitud.
    if (raw.includes("-")) return raw;
    return raw.slice(0, 2) + (raw.length > 2 ? "-" + raw.slice(2) : "");
  };
  document.querySelectorAll("input[data-mask]").forEach((input) => {
    const dni = input.dataset.mask === "dni";
    const format = dni ? formatDni : formatExpediente;
    const legacy = input.dataset.legacyValue;
    const valid = dni ? /^[0-9]{2}\.[0-9]{3}\.[0-9]{3}$/ : /^[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}$/;
    const message = dni ? "Ingresá exactamente 8 dígitos." :
      "Usá el formato 01-758-2026; el bloque central es un número entre 1 y 9999.";
    let composing = false;
    const update = () => {
      if (composing) return;
      if (legacy && input.value === legacy) {
        input.setCustomValidity("");
        return;
      }
      const value = input.value;
      const start = input.selectionStart;
      const end = input.selectionEnd;
      const formatted = format(value);
      if (formatted !== value) {
        input.value = formatted;
        // Transformar también los prefijos conserva la posición de la edición.
        input.setSelectionRange(format(value.slice(0, start)).length, format(value.slice(0, end)).length);
      }
      input.setCustomValidity(!input.value || valid.test(input.value) ? "" : message);
    };
    input.addEventListener("compositionstart", () => { composing = true; });
    input.addEventListener("compositionend", () => { composing = false; update(); });
    input.addEventListener("input", update);
    const separator = input.nextElementSibling;
    if (!dni && separator && separator.hasAttribute("data-mask-separator")) {
      separator.hidden = false;
      separator.addEventListener("click", () => {
        input.setRangeText("-", input.selectionStart, input.selectionEnd, "end");
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus({ preventScroll: true });
      });
    }
    input.addEventListener("beforeinput", (event) => {
      if (composing || input.value === legacy) return;
      const start = input.selectionStart;
      if (!dni || start !== input.selectionEnd) return;
      const backwards = event.inputType === "deleteContentBackward";
      const forwards = event.inputType === "deleteContentForward";
      // Borrar junto a un punto elimina el dígito contiguo; nunca deja el cursor atrapado.
      if ((backwards && input.value[start - 1] === ".") || (forwards && input.value[start] === ".")) {
        event.preventDefault();
        const from = backwards ? start - 2 : start;
        const to = backwards ? start : start + 2;
        input.setRangeText("", from, to, "start");
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    update();
  });
})();
