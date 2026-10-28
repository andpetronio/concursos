/* SDD-006/4C: habilitación visual de formularios embebidos.
 * La validación real y la autorización se ejecutan SIEMPRE en Django. */
(() => {
  'use strict';
  const attach = root => {
    root.querySelectorAll('[data-document-inline-form]').forEach(form => {
      if (form.dataset.initialized === 'true') return;
      form.dataset.initialized = 'true';
      const button = form.querySelector('[data-document-generate-button]');
      const help = form.querySelector('[data-document-generation-help]');
      const complements = form.querySelector('.document-inline-complements');
      const state = form.closest('.document-generation-row')?.querySelector('.document-generation-state');
      if (!button || !complements) return;
      const update = () => {
        // No pretendemos evaluar las reglas administrativas en el navegador.
        const ready = form.checkValidity();
        button.disabled = !ready;
        if (state) {
          state.classList.toggle('is-ready', ready);
          state.classList.toggle('is-pending', !ready);
          state.textContent = ready ? 'Listo para generar' : 'Completar datos del borrador';
        }
        if (help) help.textContent = ready
          ? 'Datos complementarios completos. La generación se verificará en el servidor.'
          : 'Completá los campos y las confirmaciones para habilitar el botón.';
      };
      form.addEventListener('input', update);
      form.addEventListener('change', update);
      form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
          event.preventDefault();
          complements.open = true;
          form.reportValidity();
          return;
        }
        button.disabled = true;
        if (help) help.textContent = 'Generando y conservando el borrador…';
      });
      update();
    });
  };
  attach(document);
  // La disponibilidad se puede reemplazar por HTML recibido del servidor.
  const panel = document.getElementById('panel-documentos');
  if (panel && typeof MutationObserver === 'function') {
    new MutationObserver(() => attach(panel)).observe(panel, {childList: true, subtree: true});
  }
})();
