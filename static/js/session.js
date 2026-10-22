(() => {
  "use strict";
  const root = document.querySelector("[data-session-activity]");
  if (!root) return;
  const channel = "BroadcastChannel" in window ? new BroadcastChannel("concursos-session") : null;
  let lastSent = 0;
  let timer;
  let pending = false;
  function expired() { window.location.replace(`${root.dataset.login}?expired=1`); }
  function schedule(seconds = 1800) {
    clearTimeout(timer);
    timer = setTimeout(check, Math.max(1, seconds) * 1000 + 250);
  }
  async function check() {
    try {
      // Consultar el estado nunca renueva: contempla actividad en otras pestañas.
      const response = await fetch(root.dataset.sessionStatus, {credentials: "same-origin", cache: "no-store"});
      if (response.status === 401 || response.redirected) return expired();
      if (response.ok) schedule((await response.json()).expires_in);
    } catch { schedule(30); }
  }
  async function interact(event) {
    if (!event.isTrusted || document.visibilityState !== "visible" || pending) return;
    if (Date.now() - lastSent < 45000) return;
    const token = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
    if (!token) return;
    pending = true;
    lastSent = Date.now();
    try {
      const response = await fetch(root.dataset.sessionActivity, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: {"X-CSRFToken": token},
      });
      if (response.status === 401 || response.redirected) return expired();
      if (response.ok) { schedule(); channel?.postMessage("activity"); }
    } catch { lastSent = 0; }
    finally { pending = false; }
  }
  for (const name of ["pointerdown", "keydown", "input", "wheel", "touchstart"]) {
    document.addEventListener(name, interact, {passive: true});
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") check();
  });
  if (channel) channel.onmessage = () => check();
  check();
})();
