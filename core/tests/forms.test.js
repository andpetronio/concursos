/* Ejecutar: node --test core/tests/forms.test.js */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const { join } = require("node:path");

const script = readFileSync(join(__dirname, "../../static/js/forms.js"), "utf8");
function createInput(kind, value, legacy = "") {
  const handlers = {};
  return {
    value, dataset: { mask: kind, ...(legacy ? { legacyValue: legacy } : {}) },
    selectionStart: value.length, selectionEnd: value.length,
    validMessage: null,
    addEventListener(name, callback) { handlers[name] = callback; },
    setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; },
    setCustomValidity(message) { this.validMessage = message; },
    dispatchEvent(event) { handlers[event.type]?.(event); },
    input(value, event = {}) {
      this.value = value;
      this.selectionStart = value.length;
      this.selectionEnd = value.length;
      handlers.input(event);
    },
    get handlers() { return handlers; },
  };
}
function attach(input) {
  runInNewContext(script, { document: { querySelectorAll: () => [input] }, Event: class Event {
    constructor(type) { this.type = type; }
  } });
  return input;
}

test("DNI: visual de diez caracteres sin perder ceros", () => {
  const input = attach(createInput("dni", "00123456"));
  assert.equal(input.value, "00.123.456");
  assert.equal(input.validMessage, "");
  input.input("1234567");
  assert.equal(input.value, "12.345.67");
  assert.ok(input.validMessage);
});

test("Teléfono: máscara de 11 caracteres al pegar diez dígitos", () => {
  const input = attach(createInput("telefono", ""));
  input.input("2641234567", { inputType: "insertFromPaste" });
  assert.equal(input.value, "264-1234567");
  assert.equal(input.validMessage, "");
  input.input("264-123");
  assert.ok(input.validMessage);
});

test("Expediente: bloque central variable, segundo guion manual o pegado completo", () => {
  const input = attach(createInput("expediente", ""));
  input.input("01758");
  assert.equal(input.value, "01-758");
  input.input("01-758-2026");
  assert.equal(input.value, "01-758-2026");
  assert.equal(input.validMessage, "");
  input.input("017582026", { inputType: "insertFromPaste" });
  assert.equal(input.value, "01-758-2026");
  input.input("0112342026");
  assert.equal(input.value, "01-1234-2026");
  assert.equal(input.validMessage, "");
});

test("Teléfono legado: conservar la entrada existente sin transformarla", () => {
  const input = attach(createInput("telefono", "2", "2"));
  assert.equal(input.value, "2");
  assert.equal(input.validMessage, "");
  input.input("2641234567");
  assert.equal(input.value, "264-1234567");
});
