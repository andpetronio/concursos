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
        const jurados = [...form.querySelectorAll('[name="jurados_presentes"]')];
        const juradoElegido = jurados.length === 0 || jurados.some(input => input.checked);
        const ready = form.checkValidity() && juradoElegido;
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
        const jurados = [...form.querySelectorAll('[name="jurados_presentes"]')];
        if (!form.checkValidity() || (jurados.length > 0 && !jurados.some(input => input.checked))) {
          event.preventDefault();
          complements.open = true;
          if (jurados.length > 0 && !jurados.some(input => input.checked)) {
            jurados[0].focus();
            if (help) help.textContent = 'Marcá al menos un jurado presente.';
          } else {
            form.reportValidity();
          }
          return;
        }
        button.disabled = true;
        if (help) help.textContent = 'Generando y conservando el borrador…';
      });
      update();
    });
  };
  // La lista es nativa: JavaScript solo mejora el resumen y la visibilidad de los
  // campos condicionales. Sin JavaScript todo el formulario sigue siendo usable.
  const attachSorteo = root => {
    root.querySelectorAll('[data-sorteo-form]').forEach(group => {
      if (group.dataset.initialized === 'true') return;
      group.dataset.initialized = 'true';
      const form = group.closest('form');
      const jurados = group.querySelector('[name="jurados_presentes"]');
      const aspirantes = group.querySelector('[name="aspirantes_presentes"]');
      const radio = group.querySelector('[data-veedor-group]');
      const summary = group.querySelector('[data-sorteo-summary]');
      if (!form || !jurados || !aspirantes || !radio || !summary) return;
      const count = name => group.querySelectorAll(`[name="${name}"]:checked`).length;
      const update = () => {
        group.querySelectorAll('[data-attendees-group]').forEach(fieldset => {
          const name = fieldset.querySelector('input[type="checkbox"]')?.name;
          const badge = fieldset.querySelector('[data-attendees-count]');
          if (!badge || !name) return;
          const amount = count(name);
          badge.hidden = false;
          badge.textContent = `${amount} ${amount === 1 ? 'persona seleccionada' : 'personas seleccionadas'}`;
        });
        const presence = radio.querySelector('input[type="radio"]:checked')?.value || '';
        group.querySelectorAll('[data-veedor-detail]').forEach(detail => {
          detail.hidden = detail.dataset.veedorDetail !== presence;
        });
        const veedorLabel = {
          presente: 'presente',
          ausente: 'designado, ausente',
          sin_designacion: 'sin designación informada'
        }[presence] || 'sin especificar';
        summary.textContent = `Para el borrador: ${count('jurados_presentes')} jurado(s), ` +
          `${count('aspirantes_presentes')} aspirante(s). Veedor gremial: ${veedorLabel}.`;
      };
      form.addEventListener('change', update);
      update();
    });
  };
  attach(document);
  attachSorteo(document);
  // La disponibilidad se puede reemplazar por HTML recibido del servidor.
  const panel = document.getElementById('panel-documentos');
  if (panel && typeof MutationObserver === 'function') {
    new MutationObserver(() => { attach(panel); attachSorteo(panel); }).observe(panel, {childList: true, subtree: true});
  }
})();
