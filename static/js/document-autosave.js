/* Verificación documental: guardado inmediato y secuencial por requisito.
   Reutiliza el POST transaccional del servidor (CSRF, permisos, versión e historial).
   Sin JS / fetch el botón Guardar clásico permanece disponible. */
(() => {
  'use strict';
  if (typeof fetch !== 'function' || typeof FormData !== 'function') return;

  const forms = document.querySelectorAll('.document-toggle-form');
  const states = [];
  const isEqual = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const digits = /^[0-9]{1,2}$/;

  function fojasValidas(texto) {
    const match = /^([0-9]+)\s*(?:\/\s*([0-9]+))?$/.exec(texto.trim());
    if (!match || match[1].length > 50 || (match[2] && match[2].length > 50)) return false;
    const inicio = Number(match[1]);
    const final = match[2] === undefined ? inicio : Number(match[2]);
    return Number.isSafeInteger(inicio) && Number.isSafeInteger(final) && inicio >= 1 && final >= inicio;
  }

  function actualizarResumen(totales) {
    if (!totales) return;
    const setText = (selector, value) => {
      const node = document.querySelector(selector);
      if (node) node.textContent = String(value);
    };
    setText('[data-document-complete-count]', totales.completos);
    setText('[data-document-pending-count]', totales.pendientes);
    setText('[data-document-future-count]', totales.futuros);
    Object.entries(totales.secciones || {}).forEach(([codigo, info]) => {
      const element = document.querySelector(`[data-document-section-progress="${codigo}"]`);
      if (!element) return;
      element.textContent = `${info.completos}/${info.total} completos`;
      element.setAttribute('aria-label', `${info.completos} de ${info.total} requisitos completos`);
    });
  }

  forms.forEach(form => {
    const status = form.querySelector('[data-document-auto-status]');
    const retry = form.querySelector('[data-document-auto-retry]');
    const reload = form.querySelector('[data-document-auto-reload]');
    const fallback = form.querySelector('[data-document-fallback-save]');
    const toggle = form.querySelector('input[type="checkbox"]');
    const version = form.querySelector('input[name$="-version_esperada"]');
    if (!status || !retry || !reload || !fallback || !toggle || !version) return;

    const fields = [...form.querySelectorAll('input, textarea, select')]
      .filter(field => !field.disabled && !['hidden', 'submit', 'button'].includes(field.type));
    const read = () => fields.map(field => field.type === 'checkbox' ? field.checked : field.value);
    const fojas = form.querySelector('input[name$="-fojas"]');
    const ppal = form.querySelector('input[name$="-partida_principal"]');
    const activ = form.querySelector('input[name$="-actividad_presupuestaria"]');
    const observaciones = form.querySelector('textarea[name$="-observaciones"]');
    let saved = read();
    let busy = false;
    let blocked = false;
    let shouldRetry = false;
    fallback.hidden = true;

    const dirty = () => !isEqual(saved, read());
    const feedback = (mensaje, {failure = false, pending = false} = {}) => {
      status.textContent = mensaje;
      form.dataset.documentSaveError = String(failure);
      form.dataset.documentLocalPending = String(pending);
      retry.hidden = !(failure && !blocked);
      reload.hidden = !blocked;
    };
    const reasonIncomplete = () => {
      if (!toggle.checked) return '';
      if (form.dataset.documentFojasRequired === 'true' && fojas && !fojasValidas(fojas.value))
        return 'Completá una foja válida para registrar la verificación.';
      if (form.dataset.documentBudgetRequired === 'true' &&
          (!ppal || !activ || !digits.test(ppal.value.trim()) || !digits.test(activ.value.trim())))
        return 'Completá PPAL y ACTIV (uno o dos dígitos) antes de verificar.';
      return '';
    };
    const syncSave = (data) => {
      version.value = String(data.version);
      // No sobrescribir ediciones nuevas realizadas mientras el servidor respondía.
      const current = read();
      const names = fields.map(field => field.name);
      const normalized = {
        verificado: data.verificado,
        fojas: data.fojas,
        partida_principal: data.partida_principal,
        actividad_presupuestaria: data.actividad_presupuestaria,
        observaciones: data.observaciones,
      };
      const submitted = inFlightValues;
      fields.forEach((field, i) => {
        const suffix = names[i].split('-').pop();
        if (!(suffix in normalized) || current[i] !== submitted[i]) return;
        if (field.type === 'checkbox') field.checked = !!normalized[suffix];
        else field.value = normalized[suffix] ?? '';
      });
      saved = fields.map((field, i) => {
        const suffix = names[i].split('-').pop();
        return suffix in normalized ? normalized[suffix] : submitted[i];
      });
      const row = form.closest('.document-control');
      if (row) {
        const state = row.querySelector('[data-document-state]');
        if (state) {
          state.textContent = data.estado;
          state.className = `document-control-status document-control-status--${data.estado_clase}`;
        }
        const text = (selector, value) => {
          const elem = row.querySelector(selector);
          if (elem) elem.textContent = value || 'Sin registrar';
        };
        text('[data-document-fojas]', data.fojas);
        text('[data-document-ppal]', data.partida_principal);
        text('[data-document-activ]', data.actividad_presupuestaria);
        const facts = row.querySelector('[data-document-facts]');
        if (facts) {
          const note = facts.querySelector('[data-document-has-notes]');
          if (data.observaciones && !note) {
            const span = document.createElement('span');
            span.setAttribute('data-document-has-notes', '');
            span.textContent = 'Observaciones registradas';
            facts.append(span);
          } else if (!data.observaciones && note) note.remove();
        }
        const summary = row.querySelector('.document-control-notes > summary');
        if (summary) summary.textContent = data.observaciones ? 'Observaciones (registradas)' : 'Observaciones';
        const meta = row.querySelector('[data-document-meta]');
        if (meta) {
          meta.replaceChildren();
          const stamp = document.createElement('span');
          stamp.textContent = `Actualizado por ${data.usuario} · ${data.actualizado_en}`;
          const link = document.createElement('a');
          link.href = data.historial_url;
          link.textContent = 'Ver historial de correcciones';
          meta.append(stamp, link);
        }
      }
      // Actualizar también la etapa y la exigibilidad tras el quinto previo.
      const etapa = data.etapa_documental;
      if (etapa) {
        const titulo = document.querySelector('[data-document-stage-name]');
        if (titulo) titulo.textContent = etapa.nombre;
        const editor = document.querySelector('.document-stage-editor');
        if (editor) {
          const selector = editor.querySelector('select[name="etapa-etapa"]');
          const versionEtapa = editor.querySelector('input[name="etapa-version_esperada"]');
          if (selector) selector.value = etapa.codigo;
          if (versionEtapa) versionEtapa.value = String(etapa.version);
        }
      }
      Object.entries(data.estados_controles || {}).forEach(([id, valor]) => {
        const fila = document.getElementById(`documental-${id}`);
        const etiqueta = fila?.querySelector('[data-document-state]');
        if (!etiqueta) return;
        etiqueta.textContent = valor.estado;
        etiqueta.className = `document-control-status document-control-status--${valor.clase}`;
      });
      actualizarResumen(data.totales);
      const guidance = document.querySelector('[data-document-guidance]');
      if (guidance && typeof data.habilitacion_html === 'string') guidance.innerHTML = data.habilitacion_html;
    };
    let inFlightValues = null;

    async function flush() {
      if (busy || blocked || !dirty()) return;
      const motivo = reasonIncomplete();
      if (motivo) { feedback(motivo, {pending: true}); return; }
      busy = true;
      shouldRetry = false;
      inFlightValues = read();
      form.dataset.documentSaving = 'true';
      feedback('Guardando…', {pending: true});
      try {
        const response = await fetch(form.action.split('#')[0], {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
          headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
        });
        const data = response.headers.get('content-type')?.includes('application/json')
          ? await response.json() : null;
        if (!response.ok || !data?.ok) {
          if (response.status === 409) {
            blocked = true;
            feedback('Otro operador modificó este requisito. Recargá la ficha antes de continuar.', {failure: true});
            return;
          }
          const messages = data?.errores
            ? Object.values(data.errores).flat().join(' ') : '';
          shouldRetry = true;
          feedback(messages || 'No se pudo guardar. Revisá la conexión o tu sesión.', {failure: true});
          return;
        }
        syncSave(data);
        feedback('Guardado');
      } catch (e) {
        shouldRetry = true;
        feedback('No se pudo guardar. Comprobá la conexión y reintentá.', {failure: true});
      } finally {
        busy = false;
        form.dataset.documentSaving = 'false';
        inFlightValues = null;
        // Serializar cambios que el operador haya realizado mientras llegaba la respuesta.
        if (!shouldRetry && !blocked && dirty()) void flush();
      }
    }

    function changed(event) {
      if (blocked) return;
      if (!dirty()) { feedback(''); return; }
      // Toggle inmediato; texto al finalizar (change/blur), nunca cada tecla.
      if (event.type === 'change' || event.type === 'submit') void flush();
      else feedback('Pendiente: al salir del campo se guardarán los cambios.', {pending: true});
    }
    form.addEventListener('input', changed);
    form.addEventListener('change', changed);
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!blocked) void flush();
    });
    retry.addEventListener('click', () => { if (!blocked) void flush(); });
    states.push(() => busy || dirty());
    // Si JS se ejecutó correctamente, el botón tradicional deja de ser necesario.
    feedback(form.classList.contains('document-toggle-form--errors')
      ? 'Revisá los datos señalados para guardar automáticamente.' : '');
  });

  window.addEventListener('beforeunload', event => {
    if (!states.some(pending => pending())) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
