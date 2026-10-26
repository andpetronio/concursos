/* Máscaras progresivas: solo presentación; Django valida todo envío. */
(() => {
  "use strict";
  const digits = (value) => value.replace(/[^0-9]/g, "");
  const formatDni = (value) => {
    const raw = digits(value).slice(0, 8);
    return raw.slice(0, 2) + (raw.length > 2 ? "." + raw.slice(2, 5) : "") +
      (raw.length > 5 ? "." + raw.slice(5) : "");
  };
  const formatTelefono = (value) => {
    const raw = digits(value).slice(0, 10);
    return raw.slice(0, 3) + (raw.length > 3 ? "-" + raw.slice(3) : "");
  };
  const formatExpediente = (value, pasted = false) => {
    const safe = value.replace(/[^0-9-]/g, "");
    const raw = digits(safe);
    // Al pegar el número completo sin guiones, reservar sus últimos 4 dígitos para el año.
    if (pasted && !safe.includes("-") && raw.length >= 7 && raw.length <= 10 &&
        /^[1-9][0-9]{0,3}$/.test(raw.slice(2, -4))) {
      return raw.slice(0, 2) + "-" + raw.slice(2, -4) + "-" + raw.slice(-4);
    }
    const prefix = raw.slice(0, 2);
    if (prefix.length < 2) return prefix;
    const withoutPrefix = safe.replace(/^[0-9]{2}/, "");
    const rest = withoutPrefix.startsWith("-") ? withoutPrefix.slice(1) : withoutPrefix;
    const parts = rest.split("-");
    const central = digits(parts[0]).slice(0, 4);
    const overflow = digits(parts[0]).slice(4);
    const hasYear = parts.length > 1 || overflow.length > 0;
    const year = (overflow + parts.slice(1).join("").replace(/[^0-9]/g, "")).slice(0, 4);
    return prefix + (rest || safe.includes("-") ? "-" : "") + central +
      (hasYear ? "-" + year : "");
  };

  document.querySelectorAll("input[data-mask]").forEach((input) => {
    const kind = input.dataset.mask;
    const format = kind === "dni" ? formatDni : kind === "telefono" ? formatTelefono : formatExpediente;
    const legacy = input.dataset.legacyValue;
    const valid = kind === "dni" ? /^[0-9]{2}\.[0-9]{3}\.[0-9]{3}$/ :
      kind === "telefono" ? /^[0-9]{3}-[0-9]{7}$/ : /^[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}$/;
    const message = kind === "dni" ? "Ingresá exactamente 8 dígitos." :
      kind === "telefono" ? "Usá el formato 999-9999999 (10 dígitos)." :
      "Usá el formato 01-758-2026; separá el número del año con un guion.";
    let composing = false;
    const update = (event) => {
      if (composing) return;
      if (legacy && input.value === legacy) {
        input.setCustomValidity("");
        return;
      }
      const value = input.value;
      const start = input.selectionStart;
      const end = input.selectionEnd;
      const pasted = kind === "expediente" && event?.inputType === "insertFromPaste";
      const formatted = format(value, pasted);
      if (formatted !== value) {
        input.value = formatted;
        // El pegado de un expediente completo termina al final. Al teclear se conserva el cursor.
        if (pasted) {
          input.setSelectionRange(formatted.length, formatted.length);
        } else if (start !== null && end !== null) {
          input.setSelectionRange(format(value.slice(0, start)).length, format(value.slice(0, end)).length);
        }
      }
      input.setCustomValidity(!input.value || valid.test(input.value) ? "" : message);
    };
    input.addEventListener("compositionstart", () => { composing = true; });
    input.addEventListener("compositionend", () => { composing = false; update(); });
    input.addEventListener("input", update);
    input.addEventListener("beforeinput", (event) => {
      if (kind !== "dni" || composing || input.value === legacy ||
          input.selectionStart !== input.selectionEnd) return;
      const start = input.selectionStart;
      const backwards = event.inputType === "deleteContentBackward";
      const forwards = event.inputType === "deleteContentForward";
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
