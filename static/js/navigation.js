(() => {
  "use strict";
  const panel = document.getElementById("primary-navigation");
  const toggle = document.querySelector(".navigation-toggle");
  const closeButton = document.querySelector("[data-navigation-close]");
  const backdrop = document.querySelector("[data-navigation-backdrop]");
  if (!panel || !toggle || !closeButton || !backdrop) return;

  const mobile = window.matchMedia("(max-width: 760px)");
  const background = [...document.querySelectorAll(".workspace, .skip-link")];
  const previousInert = new Map();
  let opened = false;
  let lastFocused = document.activeElement;
  document.addEventListener("focusin", event => { lastFocused = event.target; });
  const focusable = () => [...panel.querySelectorAll("a[href], button:not(:disabled), [tabindex='0']")]
    .filter(element => !element.hidden && element.getClientRects().length);

  function close(returnFocus = true) {
    opened = false;
    toggle.setAttribute("aria-expanded", "false");
    toggle.hidden = !mobile.matches;
    closeButton.hidden = !mobile.matches;
    panel.hidden = mobile.matches;
    panel.removeAttribute("role");
    panel.removeAttribute("aria-modal");
    backdrop.hidden = true;
    document.body.classList.remove("navigation-open");
    for (const [element, inert] of previousInert) element.inert = inert;
    previousInert.clear();
    if (returnFocus && mobile.matches) toggle.focus();
  }

  function open() {
    if (!mobile.matches) return;
    opened = true;
    panel.hidden = false;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    toggle.setAttribute("aria-expanded", "true");
    backdrop.hidden = false;
    document.body.classList.add("navigation-open");
    for (const element of background) {
      previousInert.set(element, element.inert);
      element.inert = true;
    }
    closeButton.focus();
  }

  toggle.addEventListener("click", () => opened ? close() : open());
  closeButton.addEventListener("click", () => close());
  backdrop.addEventListener("click", () => close());
  panel.addEventListener("click", event => {
    // No devolución de foco al disparador antes de seguir el enlace.
    if (opened && event.target.closest("a[href]")) close(false);
  });
  document.addEventListener("keydown", event => {
    if (!opened) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "Tab") {
      const controls = focusable();
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  mobile.addEventListener("change", () => {
    // A media-query display change can blur a mobile control before this event.
    const focused = document.activeElement === document.body ? lastFocused : document.activeElement;
    const focusedInPanel = panel.contains(focused);
    close(false);
    if (mobile.matches && focusedInPanel) {
      toggle.focus();
    } else if (!mobile.matches && (focused === closeButton || focused === toggle)) {
      const firstLink = [...panel.querySelectorAll("nav a[href]")]
        .find(element => element.getClientRects().length);
      if (firstLink) firstLink.focus();
    }
  });
  panel.classList.add("navigation-enhanced");
  close(false);
})();
