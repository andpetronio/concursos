/* Temarios: editor local sin dependencias. El servidor valida un subconjunto estricto de HTML. */
(() => {
  'use strict';
  const allowed = new Set(['P','DIV','UL','OL','LI','BR','STRONG','B','EM','I','U']);
  const makeSafe = (html) => {
    const source = new DOMParser().parseFromString(html, 'text/html').body;
    const container = document.createElement('div');
    const transfer = (from, to) => {
      for (const node of from.childNodes) {
        if (node.nodeType === Node.TEXT_NODE) {
          to.appendChild(document.createTextNode(node.textContent));
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          if (['SCRIPT','STYLE','IFRAME','OBJECT','SVG','IMG'].includes(node.tagName)) continue;
          if (!allowed.has(node.tagName)) {
            transfer(node, to); // Descarta el contenedor no admitido y sus atributos.
            continue;
          }
          const tag = ({B:'strong', I:'em', DIV:'div'})[node.tagName] || node.tagName.toLowerCase();
          const safe = document.createElement(tag);
          transfer(node, safe);
          to.appendChild(safe);
        }
      }
    };
    transfer(source, container);
    return container.innerHTML;
  };
  const attach = root => {
    root.querySelectorAll('textarea[data-richtext="temario"]:not([data-richtext-ready])').forEach(input => {
      input.dataset.richtextReady = 'true';
      const container = document.createElement('div');
      container.className = 'sorteo-richtext';
      const toolbar = document.createElement('div');
      toolbar.className = 'sorteo-richtext-toolbar';
      toolbar.setAttribute('role', 'toolbar');
      toolbar.setAttribute('aria-label', `Formato de ${input.name === 'tema_teoria' ? 'tema teórico' : 'tema práctico'}`);
      const editor = document.createElement('div');
      editor.className = 'sorteo-richtext-editor';
      editor.contentEditable = 'true';
      editor.setAttribute('role', 'textbox');
      editor.setAttribute('aria-multiline', 'true');
      editor.setAttribute('aria-label', input.closest('.field')?.querySelector('label')?.textContent || input.name);
      editor.dataset.placeholder = 'Escribí el temario y aplicá el formato necesario…';
      if (input.value.trim().startsWith('<')) {
        editor.innerHTML = makeSafe(input.value);
      } else {
        // Texto plano histórico: nunca interpretar como HTML sin que venga marcado.
        const lines = input.value.split(/\r?\n/);
        if (input.value) lines.forEach(line => { const p = document.createElement('p'); p.textContent = line; editor.appendChild(p); });
      }
      const actions = [
        ['bold', 'N', 'Negrita'], ['italic', 'C', 'Cursiva'], ['underline', 'S', 'Subrayado'],
        ['insertUnorderedList', '• Lista', 'Lista con viñetas'],
        ['insertOrderedList', '1. Lista', 'Lista numerada']
      ];
      for (const [command, title, label] of actions) {
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'sorteo-richtext-tool';
        button.textContent = title; button.setAttribute('aria-label', label);
        button.setAttribute('title', label);
        if (command === 'bold') button.style.fontWeight = 'bold';
        if (command === 'italic') button.style.fontStyle = 'italic';
        if (command === 'underline') button.style.textDecoration = 'underline';
        button.addEventListener('mousedown', event => event.preventDefault());
        button.addEventListener('click', () => {
          editor.focus();
          document.execCommand('styleWithCSS', false, 'false');
          document.execCommand(command, false, null);
          sync();
        });
        toolbar.appendChild(button);
      }
      const hint = document.createElement('p');
      hint.className = 'field-help';
      hint.textContent = 'Se conservarán las viñetas, la numeración, negritas, cursivas y subrayados en el DOCX.';
      container.append(toolbar, editor, hint);
      input.insertAdjacentElement('afterend', container);
      // Sin JavaScript permanece la textarea nativa; al activar, se sincroniza HTML.
      input.classList.add('sorteo-richtext-source');
      input.required = false;
      const sync = () => {
        input.value = makeSafe(editor.innerHTML);
        input.dispatchEvent(new Event('input', { bubbles: true }));
      };
      editor.addEventListener('input', sync);
      editor.addEventListener('blur', sync);
      editor.addEventListener('paste', event => {
        event.preventDefault();
        const plain = event.clipboardData?.getData('text/plain') || '';
        document.execCommand('insertText', false, plain);
        sync();
      });
      const form = input.closest('form');
      if (form && !form.dataset.richtextValidation) {
        form.dataset.richtextValidation = 'true';
        form.addEventListener('submit', event => {
          const editors = [...form.querySelectorAll('textarea[data-richtext-ready]')];
          for (const textarea of editors) {
            const surface = textarea.nextElementSibling?.querySelector('.sorteo-richtext-editor');
            if (!surface) continue;
            textarea.value = makeSafe(surface.innerHTML);
            if (!surface.textContent.trim()) {
              event.preventDefault();
              event.stopImmediatePropagation();
              surface.focus();
              const group = textarea.closest('.document-inline-complements');
              if (group) group.open = true;
              return;
            }
          }
        }, true);
      }
      // Evitar deshabilitar el botón por la textarea visualmente sustituida.
      sync();
    });
  };
  attach(document);
  const panel = document.getElementById('panel-documentos');
  if (panel && typeof MutationObserver === 'function') {
    new MutationObserver(() => attach(panel)).observe(panel, {childList: true, subtree: true});
  }
})();
