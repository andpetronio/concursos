/* Progressive, manually activated tabs. Original fragment targets remain canonical. */
(() => {
  'use strict';
  const root = document.querySelector('[data-detail-tabs]');
  if (!root) return;
  const nav = root.querySelector('[data-detail-tab-navigation]');
  const panels = [...root.querySelectorAll('[data-detail-panel]')];
  const links = nav ? [...nav.querySelectorAll('a')] : [];
  const hint = root.querySelector('[data-detail-tabs-help]');
  const disposers = [];
  const listen = (node, event, handler) => {
    node.addEventListener(event, handler);
    disposers.push(() => node.removeEventListener(event, handler));
  };
  const fragmentTarget = hash => {
    try { return document.getElementById(decodeURIComponent(hash.slice(1))); }
    catch { return null; }
  };
  const panelFor = target => {
    const panel = target?.closest('[data-detail-panel]');
    return panels.includes(panel) ? panel : null;
  };
  const restore = () => {
    disposers.forEach(dispose => dispose());
    root.removeAttribute('data-tabs-ready');
    nav?.removeAttribute('role');
    links.forEach(link => ['role', 'aria-selected', 'aria-controls', 'tabindex'].forEach(name => link.removeAttribute(name)));
    panels.forEach(panel => {
      panel.hidden = false;
      ['role', 'aria-labelledby', 'tabindex'].forEach(name => panel.removeAttribute(name));
    });
    if (hint) hint.hidden = true;
  };
  try {
    const entries = links.map(link => ({link, panel: panelFor(fragmentTarget(link.hash))}));
    if (!entries.length || entries.length !== panels.length || new Set(entries.map(e => e.panel)).size !== panels.length || entries.some(e => !e.panel)) return;
    const updateHint = () => {
      if (!hint) return;
      const before = nav.scrollLeft > 2;
      const after = nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 2;
      hint.hidden = !(before || after);
      hint.textContent = before && after ? '← Más pestañas en ambas direcciones →' : before ? '← Más pestañas a la izquierda' : 'Más pestañas a la derecha →';
    };
    const revealTab = link => {
      const item = link.getBoundingClientRect(), viewport = nav.getBoundingClientRect();
      if (item.left < viewport.left) nav.scrollLeft -= viewport.left - item.left;
      else if (item.right > viewport.right) nav.scrollLeft += item.right - viewport.right;
      updateHint();
    };
    const select = (panel, {focus = false} = {}) => {
      entries.forEach(entry => {
        const selected = entry.panel === panel;
        entry.panel.hidden = !selected;
        entry.link.setAttribute('aria-selected', String(selected));
        entry.link.tabIndex = selected ? 0 : -1;
        if (selected) {
          if (focus) entry.link.focus({preventScroll: true});
          revealTab(entry.link);
        }
      });
    };
    const writeHash = (hash, replace = false) => {
      if (location.hash !== hash) history[replace ? 'replaceState' : 'pushState'](null, '', location.pathname + location.search + hash);
    };
    const scrollTarget = target => {
      // Opening an existing collapsed document block must not conceal a deep link.
      for (let parent = target?.parentElement; parent && parent !== root; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') parent.open = true;
      }
      target?.scrollIntoView({block: 'start'});
    };
    const fromLocation = () => {
      const target = fragmentTarget(location.hash);
      select(panelFor(target) || panels[0]);
      if (panelFor(target)) scrollTarget(target);
    };
    entries.forEach(({link, panel}, index) => {
      link.id = `detail-tab-${index}`;
      link.setAttribute('role', 'tab');
      link.setAttribute('aria-controls', panel.id);
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', link.id);
      panel.tabIndex = 0;
      listen(link, 'keydown', event => {
        const index = entries.findIndex(entry => entry.link === event.currentTarget);
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % entries.length;
        if (event.key === 'ArrowLeft') next = (index + entries.length - 1) % entries.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = entries.length - 1;
        if (next !== undefined) {
          event.preventDefault();
          links.forEach((tab, i) => { tab.tabIndex = i === next ? 0 : -1; });
          links[next].focus({preventScroll: true});
          revealTab(links[next]);
        } else if (event.key === ' ') {
          event.preventDefault();
          link.click();
        }
      });
    });
    listen(root, 'click', event => {
      const link = event.target.closest('a[href]');
      if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
      const url = new URL(link.href, location.href);
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search || !url.hash) return;
      const target = fragmentTarget(url.hash), panel = panelFor(target);
      if (!panel) return;
      event.preventDefault();
      select(panel, {focus: link.getAttribute('role') === 'tab'});
      writeHash(url.hash);
      if (link.getAttribute('role') !== 'tab') {
        panel.focus({preventScroll: true});
        scrollTarget(target);
      }
    });
    listen(window, 'hashchange', fromLocation);
    listen(window, 'popstate', fromLocation);
    listen(nav, 'scroll', updateHint);
    const layout = () => {
      const topbar = document.querySelector('.topbar');
      root.style.setProperty('--detail-topbar-height', topbar && getComputedStyle(topbar).position === 'sticky' ? `${topbar.getBoundingClientRect().height}px` : '0px');
      const selected = nav.querySelector('[aria-selected="true"]');
      if (selected) revealTab(selected);
      else updateHint();
    };
    listen(window, 'resize', layout);
    if (window.ResizeObserver) {
      const observer = new ResizeObserver(layout);
      observer.observe(nav);
      const topbar = document.querySelector('.topbar');
      if (topbar) observer.observe(topbar);
      disposers.push(() => observer.disconnect());
    }
    nav.setAttribute('role', 'tablist');
    root.setAttribute('data-tabs-ready', '');
    layout();
    // Server-rendered errors take priority even if an old hash selects another tab.
    const error = root.querySelector('.field-errors, .notice-error, .errorlist');
    const errorPanel = panelFor(error);
    if (errorPanel) {
      select(errorPanel);
      const control = error.closest('.document-control');
      writeHash(control ? `#${control.id}` : entries.find(entry => entry.panel === errorPanel).link.hash, true);
      scrollTarget(control || error);
    } else {
      fromLocation();
    }
  } catch (error) {
    restore();
    console.error('No se pudo activar la navegación por pestañas; todas las secciones siguen disponibles.', error);
  }
})();
