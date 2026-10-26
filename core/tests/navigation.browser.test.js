// Real Chromium regression. Connect only to a separately launched, temporary QA profile.
// Usage: node core/tests/navigation.browser.test.js <CDP URL> <synthetic fixture URL> <output dir>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const [endpoint, fixture, output] = process.argv.slice(2);
if (!endpoint || !fixture || !output) throw Error('Expected isolated CDP URL, synthetic fixture URL and output dir');
const pause = () => new Promise(resolve => setTimeout(resolve, 100));
(async () => {
  const tabs = await (await fetch(`${endpoint}/json/list`)).json();
  const target = tabs.find(tab => tab.type === 'page');
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener('open', resolve, {once: true}));
  let sequence = 0;
  const pending = new Map();
  const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Fetch.requestPaused') {
      const status = message.params.request.url.endsWith('/actividad/') ? 204 : 200;
      call('Fetch.fulfillRequest', {requestId:message.params.requestId, responseCode:status,
        responseHeaders:[{name:'Content-Type',value:'application/json'}],
        body:status===204 ? '' : Buffer.from('{"active":true}').toString('base64')}).catch(error=>errors.push(String(error)));
    } else if (message.id) {
      const request = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) request.reject(Error(JSON.stringify(message.error)));
      else request.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
    else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') errors.push(message.params.entry);
    else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') errors.push(message.params);
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence; pending.set(id, {resolve, reject});
    socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async expression => {
    const result = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    assert.equal(result.exceptionDetails, undefined, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const resize = async width => {
    await call('Emulation.setDeviceMetricsOverride', {width, height: 1000, deviceScaleFactor: 1, mobile: false});
    await pause();
  };
  const navigate = async url => {
    await call('Page.navigate', {url});
    for (let i = 0; i < 50; i++) {
      await pause();
      if (await evaluate(`location.href === ${JSON.stringify(url)} && document.readyState === 'complete'`)) return;
    }
    throw Error(`Page did not load: ${url}`);
  };
  const state = () => evaluate(`(() => {
    const panel = document.querySelector('#primary-navigation');
    const toggle = document.querySelector('.navigation-toggle');
    const close = document.querySelector('.navigation-close');
    const visible = e => !!e?.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
    return {width:innerWidth, panel:visible(panel), toggle:visible(toggle), close:visible(close),
      toggleDisplay:getComputedStyle(toggle).display, closeDisplay:getComputedStyle(close).display,
      expanded:toggle.getAttribute('aria-expanded'), role:panel.getAttribute('role'),
      backdrop:visible(document.querySelector('[data-navigation-backdrop]')),
      inert:document.querySelector('.workspace').inert, overflow:getComputedStyle(document.body).overflow,
      focus:document.activeElement.className, focusVisible:visible(document.activeElement),
      bodyFont:getComputedStyle(document.body).fontSize, bodyLeading:getComputedStyle(document.body).lineHeight,
      buttonFont:getComputedStyle(toggle).fontSize, buttonHeight:parseFloat(getComputedStyle(toggle).minHeight),
      tableFont:document.querySelector('.data-table') && getComputedStyle(document.querySelector('.data-table')).fontSize,
      horizontalOverflow:document.documentElement.scrollWidth > innerWidth};
  })()`);
  const click = async selector => {
    const point = await evaluate(`(() => { const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect(); return {x:${JSON.stringify(selector)} === '[data-navigation-backdrop]' ? innerWidth-8 : r.x+r.width/2,y:r.y+r.height/2}; })()`);
    await call('Input.dispatchMouseEvent', {type:'mousePressed', button:'left', clickCount:1, ...point});
    await call('Input.dispatchMouseEvent', {type:'mouseReleased', button:'left', clickCount:1, ...point});
    await pause();
  };
  const key = async (key, modifiers = 0) => {
    await call('Input.dispatchKeyEvent', {type:'keyDown', key, code:key, modifiers, windowsVirtualKeyCode:key==='Tab'?9:27});
    await call('Input.dispatchKeyEvent', {type:'keyUp', key, code:key, modifiers});
    await pause();
  };
  const screenshot = async name => {
    const {data} = await call('Page.captureScreenshot', {format:'png'});
    fs.writeFileSync(path.join(output, `${name}.png`), Buffer.from(data, 'base64'));
  };
  const results = {};
  try {
    await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable');
    await call('Network.enable'); await call('Network.setCacheDisabled', {cacheDisabled:true});
    // Static synthetic fixtures have no session backend; session behavior is covered by Django tests.
    await call('Fetch.enable', {patterns:[{urlPattern:new URL('/sesion/*',fixture).href}]});
    for (const width of [1440,1280,768,360]) {
      await resize(width); await navigate(fixture);
      const snapshot = await state(); results[width] = snapshot;
      assert.equal(snapshot.panel, width>760); assert.equal(snapshot.toggle,width<=760);
      assert.equal(snapshot.close,false); assert.equal(snapshot.horizontalOverflow,false);
      assert.equal(snapshot.bodyFont,'16px'); assert.equal(snapshot.buttonFont,'16px');
      assert.ok(snapshot.buttonHeight>=44);
      if (snapshot.tableFont) assert.equal(snapshot.tableFont,'16px');
      if (width>760) {
        // Exercise the CSS cascade independently of the JS hidden safeguard.
        await evaluate(`document.querySelectorAll('.navigation-toggle,.navigation-close').forEach(e=>e.hidden=false)`);
        const cssOnly = await state();
        assert.equal(cssOnly.toggle,false,'Desktop toggle must be hidden by the real CSS cascade');
        assert.equal(cssOnly.close,false,'Desktop close must be hidden by the real CSS cascade');
        await evaluate(`document.querySelectorAll('.navigation-toggle,.navigation-close').forEach(e=>e.hidden=true)`);
      }
      await screenshot(`ficha-${width}`);
    }
    await click('.navigation-toggle');
    let snapshot = await state(); results.mobileOpen=snapshot;
    assert.ok(snapshot.panel && snapshot.close && snapshot.backdrop && snapshot.inert);
    assert.equal(snapshot.role,'dialog'); assert.equal(snapshot.overflow,'hidden');
    assert.match(snapshot.focus,/navigation-close/); await screenshot('ficha-360-open');
    await key('Tab',8);
    assert.equal(await evaluate(`document.activeElement.closest('form')?.method`),'post');
    await key('Tab'); assert.match((await state()).focus,/navigation-close/);
    await key('Escape'); snapshot=await state();
    assert.ok(!snapshot.panel && !snapshot.inert && !snapshot.backdrop);
    assert.match(snapshot.focus,/navigation-toggle/); assert.notEqual(snapshot.overflow,'hidden');
    for (const closer of ['.navigation-close','[data-navigation-backdrop]']) {
      await click('.navigation-toggle'); await click(closer); assert.equal((await state()).panel,false);
    }
    await click('.navigation-toggle'); await resize(1280);
    snapshot=await state(); results.resizeDesktop=snapshot;
    assert.ok(snapshot.panel && !snapshot.toggle && !snapshot.close && !snapshot.inert && !snapshot.backdrop && snapshot.focusVisible);
    assert.equal(snapshot.role,null); assert.notEqual(snapshot.overflow,'hidden'); assert.match(snapshot.focus,/nav-link/);
    await resize(360); snapshot=await state();
    assert.ok(!snapshot.panel && snapshot.toggle && snapshot.focusVisible); assert.match(snapshot.focus,/navigation-toggle/);
    await click('.navigation-toggle');
    // Same-document real anchor exercises link cleanup without leaving the synthetic fixture server.
    await evaluate(`document.querySelector('#primary-navigation nav a').href='#contenido'`);
    await click('#primary-navigation nav a'); snapshot=await state();
    assert.ok(!snapshot.panel && !snapshot.inert && !snapshot.backdrop); assert.notEqual(snapshot.overflow,'hidden');
    await evaluate(`document.querySelector('.navigation-toggle').focus()`);
    await resize(1280); assert.match((await state()).focus,/nav-link/);
    await resize(360); await click('.navigation-toggle');
    await evaluate(`document.querySelector('#primary-navigation nav a').focus()`);
    await resize(1280); assert.match((await state()).focus,/nav-link/);
    await evaluate(`document.querySelector('#contenido').focus()`);
    await resize(360); assert.equal(await evaluate('document.activeElement.id'),'contenido');
    for (const width of [360,1440]) {
      await call('Emulation.setScriptExecutionDisabled',{value:true});
      await resize(width); await navigate(fixture);
      snapshot=await state(); results[`noJS-${width}`]=snapshot;
      assert.ok(snapshot.panel && !snapshot.toggle && !snapshot.close && !snapshot.inert);
      await screenshot(`ficha-${width}-nojs`);
    }
    assert.equal(errors.length,0,JSON.stringify(errors));
    results.consoleErrors=errors;
    fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify(results,null,2));
    console.log('Chromium: computed CSS desktop/mobile, density, keyboard, focus, resize, backdrop, links and no-JS passed.');
  } finally {
    await call('Fetch.disable');
    await call('Emulation.setScriptExecutionDisabled',{value:false});
    socket.close();
  }
})().catch(error => { console.error(error); process.exitCode=1; });
