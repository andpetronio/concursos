// Harness de comportamiento sin navegador ni dependencias: no sustituye QA visual.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function element() {
  const listeners = {};
  const attributes = {};
  const classes = new Set();
  return {
    hidden: false, inert: false, listeners, attributes,
    classList: { add: name => classes.add(name), remove: name => classes.delete(name), contains: name => classes.has(name) },
    setAttribute: (key, value) => { attributes[key] = value; },
    removeAttribute: key => { delete attributes[key]; },
    addEventListener: (name, listener) => { listeners[name] = listener; },
    focus() { document.activeElement = this; document.listeners.focusin?.({ target: this }); this.focusCount = (this.focusCount || 0) + 1; },
    getClientRects: () => [1],
    closest: () => null,
  };
}
const panel = element();
const toggle = element();
const closeButton = element();
const link = element();
const logout = element();
const backdrop = element();
const workspace = element();
const skip = element();
const mobile = { matches: true, addEventListener(name, fn) { this.change = fn; } };
const controls = [closeButton, link, logout];
panel.contains = node => controls.includes(node);
panel.querySelectorAll = selector => selector === "nav a[href]" ? [link] : controls;
const document = {
  activeElement: null, body: element(), listeners: {},
  getElementById: () => panel,
  querySelector: selector => ({ ".navigation-toggle": toggle, "[data-navigation-close]": closeButton, "[data-navigation-backdrop]": backdrop })[selector],
  querySelectorAll: () => [workspace, skip],
  addEventListener(name, fn) { this.listeners[name] = fn; },
};
vm.runInNewContext(fs.readFileSync("static/js/navigation.js", "utf8"), { document, window: { matchMedia: () => mobile } });
const click = node => node.listeners.click();
const key = (value, shiftKey = false) => {
  const event = { key: value, shiftKey, prevented: false, preventDefault() { this.prevented = true; } };
  document.listeners.keydown(event);
  return event;
};
assert.equal(panel.hidden, true);
assert.equal(toggle.hidden, false);
assert.equal(closeButton.hidden, false);
click(toggle);
assert.equal(panel.hidden, false);
assert.equal(toggle.attributes["aria-expanded"], "true");
assert.equal(panel.attributes["aria-modal"], "true");
assert.equal(document.activeElement, closeButton);
assert.ok(workspace.inert && skip.inert && !backdrop.hidden);
assert.ok(document.body.classList.contains("navigation-open"));
assert.equal(key("Tab", true).prevented, true);
assert.equal(document.activeElement, logout);
assert.equal(key("Tab").prevented, true);
assert.equal(document.activeElement, closeButton);
key("Escape");
assert.equal(document.activeElement, toggle);
assert.ok(panel.hidden && backdrop.hidden && !workspace.inert && !skip.inert);
assert.equal(toggle.attributes["aria-expanded"], "false");
assert.equal(panel.attributes.role, undefined);
assert.equal(document.body.classList.contains("navigation-open"), false);
for (const closer of [closeButton, backdrop]) { click(toggle); click(closer); assert.ok(panel.hidden); }
click(toggle);
const focusCount = toggle.focusCount;
panel.listeners.click({ target: { closest: () => link } });
assert.ok(panel.hidden);
assert.equal(toggle.focusCount, focusCount); // No foco artificial antes de navegar.
click(toggle);
mobile.matches = false;
document.activeElement = document.body; // Chromium blurs CSS-hidden controls before matchMedia change.
mobile.change();
assert.equal(panel.hidden, false);
assert.equal(toggle.hidden, true);
assert.equal(closeButton.hidden, true);
assert.equal(workspace.inert, false);
assert.equal(toggle.attributes["aria-expanded"], "false");
assert.equal(panel.attributes["aria-modal"], undefined);
assert.equal(document.activeElement, link); // Cerrar menú desaparece en escritorio.
mobile.matches = true;
mobile.change();
toggle.focus();
mobile.matches = false;
mobile.change();
assert.equal(document.activeElement, link); // Menú también desaparece en escritorio.
mobile.matches = true;
mobile.change();
click(toggle);
link.focus();
mobile.matches = false;
const linkFocusCount = link.focusCount;
mobile.change();
assert.equal(document.activeElement, link);
assert.equal(link.focusCount, linkFocusCount); // Enlace visible: conservar foco sin reasignarlo.
workspace.focus();
mobile.matches = true;
mobile.change();
assert.equal(document.activeElement, workspace); // Contenido visible: tampoco mover foco.
mobile.matches = false;
mobile.change();
assert.equal(document.activeElement, workspace);
mobile.matches = true;
link.focus();
mobile.change();
assert.ok(panel.hidden);
assert.equal(document.activeElement, toggle);
click(toggle);
assert.equal(document.activeElement, closeButton);
assert.equal(panel.hidden, false);
console.log("Navegación: apertura/cierre, Escape, trap/foco, enlace, fondo y resize correctos (DOM simulado).");

const tokens = fs.readFileSync("static/css/tokens.css", "utf8");
const css = fs.readFileSync("static/css/app.css", "utf8");
const color = name => tokens.match(new RegExp(`--${name}: (#[0-9A-Fa-f]{6});`))[1];
const luminance = hex => {
  const channels = hex.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
};
const ratio = (a, b) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05);
const rule = css.match(/^\.button \{([^}]+)\}/m)[1];
const fillToken = rule.match(/background: var\(--([a-z-]+)\)/)[1];
const contrast = ratio(color("background"), color(fillToken));
assert.ok(contrast >= 4.5, `Contraste botón compacto insuficiente: ${contrast.toFixed(3)}:1`);
assert.ok(ratio(color("background"), color("primary-deep")) >= 4.5);
assert.equal(color("primary"), "#C65A17");
assert.match(css, /\.button-secondary \{ background: var\(--navigation\); color: var\(--primary-ink\); border-color: var\(--border\); \}/);
assert.match(css, /\.button-secondary:hover \{ background: var\(--primary-soft\); color: var\(--primary-ink\); border-color: var\(--primary\); \}/);
console.log(`Contraste blanco/botón compacto: ${contrast.toFixed(3)}:1 (mínimo 4.5:1); identidad y secundarios conservados.`);
