// Real HTTP QA against a disposable Django server and an isolated Chrome profile.
// No request interception, HTML fixture or session mocks.
// Usage: node core/tests/workspace.browser.test.js <CDP URL> <QA origin> <output dir> [--login-only]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const [endpoint, origin, output, scope] = process.argv.slice(2);
assert(!scope || scope === '--login-only', 'Unknown QA scope');
if (!endpoint || !origin || !output) throw Error('Expected isolated CDP URL, Django QA origin and output dir');
const pause = () => new Promise(resolve => setTimeout(resolve, 100));
(async () => {
  const targets = await (await fetch(`${endpoint}/json/list`)).json();
  const target = targets.find(item => item.type === 'page');
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener('open', resolve, {once:true}));
  let sequence = 0;
  const pending = new Map();
  const errors = [];
  const network = [];
  const requestMethods = new Map();
  const browserLog = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id); pending.delete(message.id);
      if (message.error) request.reject(Error(JSON.stringify(message.error))); else request.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') errors.push('console.error');
    else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') browserLog.push({url:message.params.entry.url,text:message.params.entry.text});
    else if (message.method === 'Network.loadingFailed' && !message.params.canceled) errors.push(message.params.errorText);
    else if (message.method === 'Network.responseReceived') {
      const response = message.params.response;
      if (response.url.startsWith(origin)) network.push({path:new URL(response.url).pathname,method:requestMethods.get(message.params.requestId),status:response.status});
    } else if (message.method === 'Network.requestWillBeSent') {
      const response = message.params.redirectResponse;
      if (response?.url.startsWith(origin)) network.push({path:new URL(response.url).pathname,method:requestMethods.get(message.params.requestId),redirectStatus:response.status});
      requestMethods.set(message.params.requestId,message.params.request.method);
    }
  });
  const call = (method, params={}) => new Promise((resolve,reject) => {
    const id = ++sequence; pending.set(id,{resolve,reject}); socket.send(JSON.stringify({id,method,params}));
  });
  const evaluate = async expression => {
    const result = await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    assert.equal(result.exceptionDetails,undefined,JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const waitPage = async pathname => {
    for(let i=0;i<100;i++) { await pause(); if(await evaluate(`location.pathname === ${JSON.stringify(pathname)} && document.readyState === 'complete'`)) return; }
    throw Error(`Page did not settle at ${pathname}`);
  };
  const navigate = async pathname => {await call('Page.navigate',{url:origin+pathname});await waitPage(pathname.split('?')[0]);};
  const resize = async width => {await call('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await pause();};
  const key = async key => {await call('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:key==='Tab'?9:27});await call('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});await pause();};
  const capture = async name => {const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(shot.data,'base64'));};
  const measurements=[];
  const measure = async screen => {
    const metrics = await evaluate(`(() => {
      const visible = e => !!e?.getClientRects().length;
      const controls = [...document.querySelectorAll('.button, .field input:not([type=checkbox]):not([type=hidden]), .check-field label, .record-summary a, .record-summary button, .section-index a, .section-index button')].filter(visible);
      return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyFont:getComputedStyle(document.body).fontSize,
        minControlHeight:Math.min(...controls.map(e=>e.getBoundingClientRect().height)),
        summaryAndIndexActions:[...document.querySelectorAll('.record-summary a, .record-summary button, .section-index a, .section-index button')].filter(visible).map(e=>({label:e.textContent.trim(),height:e.getBoundingClientRect().height})),
        navigationToggle:visible(document.querySelector('.navigation-toggle')),
        headings:[...document.querySelectorAll('main h1, main h2')].map(e=>e.textContent),
        tableRegions:[...document.querySelectorAll('.table-region')].map(e=>({label:e.getAttribute('aria-label'),width:e.clientWidth,scrollWidth:e.scrollWidth})),
        anonymous:!document.querySelector('.app-shell')};
    })()`);
    assert(metrics.scrollWidth<=metrics.width,`${screen} overflow: ${JSON.stringify(metrics)}`);
    assert(metrics.minControlHeight>=43.9,`${screen} undersized control: ${JSON.stringify(metrics.summaryAndIndexActions)}`);
    assert.equal(metrics.bodyFont,'16px');
    measurements.push({screen,...metrics});
  };
  const loginChecks = [];
  const checkLoginPresentation = async width => {
    const state = await evaluate(`(() => {
      const visible = e => !!e?.getClientRects().length;
      return {width:innerWidth,brand:visible(document.querySelector('.product-name')),
        form:visible(document.querySelector('.auth-card form')),security:visible(document.querySelector('.auth-card .session-note')),
        information:[...document.querySelectorAll('.auth-introduction > :not(.product-name)')].map(e=>({tag:e.tagName,visible:visible(e),display:getComputedStyle(e).display})),
        artwork:visible(document.querySelector('.artwork-slot')),footer:visible(document.querySelector('.auth-footer')),
        columns:getComputedStyle(document.querySelector('.auth-container')).gridTemplateColumns.split(' ').length};
    })()`);
    assert(state.brand && state.form && state.security,JSON.stringify(state));
    assert(state.information.every(item=>item.visible === (width > 768)),JSON.stringify(state));
    assert.equal(state.artwork,width>768);assert.equal(state.footer,width>768);assert.equal(state.columns,width>768?2:1);
    loginChecks.push(state);
  };
  const login = async username => {
    await evaluate(`document.querySelector('#id_username').value=${JSON.stringify(username)};document.querySelector('#id_password').value='Synthetic-Only-2026!';document.querySelector('form').requestSubmit()`);
    await waitPage('/');
    assert.equal(await evaluate(`document.querySelector('.account-name').textContent`),username);
  };
  await Promise.all([call('Page.enable'),call('Runtime.enable'),call('Network.enable'),call('Log.enable')]);
  await call('Network.setCacheDisabled',{cacheDisabled:true});
  await call('Network.clearBrowserCookies');
  await resize(1280); await navigate('/ingresar/');
  assert(await evaluate(`!!document.querySelector('input[name=csrfmiddlewaretoken]')`));
  await measure('login-1280'); await checkLoginPresentation(1280); await capture('login-1280');
  await evaluate(`document.querySelector('.skip-link').focus()`); await key('Tab');
  assert.equal(await evaluate('document.activeElement.id'),'id_username');
  assert.notEqual(await evaluate('getComputedStyle(document.activeElement).boxShadow'),'none');
  for (const width of [360,768,769]) {
    await resize(width);await measure(`login-${width}`);await checkLoginPresentation(width);
    if (width===360) await capture('login-360');
  }
  await resize(360);
  await login('operador_qa');
  if (scope === '--login-only') {
    const cookies = await call('Network.getCookies',{urls:[origin]});
    assert(cookies.cookies.some(cookie=>cookie.name==='sessionid'&&cookie.httpOnly));
    assert(network.some(item=>item.path==='/ingresar/'&&item.method==='POST'&&item.redirectStatus===302));
    assert.deepEqual(errors,[]);assert.deepEqual(browserLog,[]);assert(!network.some(item=>item.status>=400));
    fs.writeFileSync(path.join(output,'login-responsive-results.json'),JSON.stringify({status:'PASS',scope:'login-only',measurements,loginChecks,network,errors,realCSRF:true,realCookies:true,sessionMocks:false},null,2));
    console.log(JSON.stringify({status:'PASS',scope:'login-only',widths:loginChecks.map(item=>item.width),errors:errors.length}));
    await call('Browser.close');socket.close();return;
  }
  await resize(1280); await measure('dashboard-1280'); await capture('dashboard-1280');
  assert(await evaluate(`!![...document.querySelectorAll('main a')].find(e=>e.textContent==='Registrar concurso')`));
  const cookies = await call('Network.getCookies',{urls:[origin]});
  assert(cookies.cookies.some(cookie=>cookie.name==='sessionid'&&cookie.httpOnly));
  await resize(360); await measure('dashboard-360'); await capture('dashboard-360');
  await evaluate(`document.querySelector('.navigation-toggle').focus();document.querySelector('.navigation-toggle').click()`);
  assert(await evaluate(`document.querySelector('.workspace').inert`));
  await key('Tab'); await key('Escape');
  assert(await evaluate(`!document.querySelector('.workspace').inert && document.activeElement.matches('.navigation-toggle')`));
  const ready = JSON.parse(fs.readFileSync(path.join(output,'ready.json'),'utf8'));
  await resize(1280); await navigate(ready.pilot); await measure('pilot-1280'); await capture('pilot-pending-1280');
  assert(await evaluate(`document.querySelector('main').textContent.includes('pendiente de aceptación')`));
  assert(await evaluate(`!!document.querySelector('a.nav-link.is-active[href="/concursos/"]')`),'QA pilot should preserve the real concursos namespace');
  assert.equal(await evaluate(`document.querySelectorAll('#aspirantes tbody tr').length`),2);
  const pilotChecks = await evaluate(`(() => {
    const anchors=[...document.querySelectorAll('.section-index a')];
    return {allAnchorsResolve:anchors.every(a=>document.querySelector(a.hash)),
      homonyms:[...document.querySelectorAll('#aspirantes tbody tr')].map(row=>row.querySelector('.person-identity span').textContent),
      juradoNameWeight:getComputedStyle(document.querySelector('#jurados .person-identity strong')).fontWeight};
  })()`);
  assert(pilotChecks.allAnchorsResolve); assert.equal(new Set(pilotChecks.homonyms).size,2); assert(Number(pilotChecks.juradoNameWeight)>=700);
  for(const id of ['jurados','control-documental','documentos']) {
    await evaluate(`document.getElementById(${JSON.stringify(id)}).scrollIntoView()`); await pause(); await capture(`pilot-pending-${id}-1280`);
  }
  await resize(360); await evaluate('scrollTo(0,0)'); await measure('pilot-360'); await capture('pilot-pending-360');
  for(const id of ['jurados','control-documental','documentos']) {
    await evaluate(`document.getElementById(${JSON.stringify(id)}).scrollIntoView()`); await pause(); await capture(`pilot-pending-${id}-360`);
  }
  const logoutGet = await evaluate(`fetch('/salir/',{redirect:'manual'}).then(r=>r.status)`);
  assert.equal(logoutGet,405);
  await evaluate(`document.querySelector('form[action="/salir/"]').requestSubmit()`); await waitPage('/ingresar/');
  await login('lector_qa'); await navigate(ready.pilot);
  assert(await evaluate(`!document.querySelector('a[href$="/editar/"]') && !document.querySelector('form[action*="control-documental"]')`));
  assert(await evaluate(`!document.querySelector('a[href*="/documentos/"][href$="/revisar/"]')`));
  await navigate(ready.detail);
  assert(await evaluate(`!document.querySelector('main').textContent.includes('Propuesta visual')`));
  await navigate('/');
  assert(await evaluate(`!document.querySelector('main').textContent.includes('Registrar concurso')`));
  await evaluate(`document.querySelector('form[action="/salir/"]').requestSubmit()`); await waitPage('/ingresar/');
  const denied = await evaluate(`fetch('/',{redirect:'manual'}).then(r=>r.type==='opaqueredirect')`);
  assert(denied,'Logged-out dashboard must redirect');
  const expectedHTTP = network.filter(item=>(item.path==='/salir/'&&item.status===405)||(item.path==='/sesion/actividad/'&&item.status===429));
  const unexpectedHTTP = network.filter(item=>item.status>=400 && !expectedHTTP.includes(item));
  const unexpectedBrowserLog = browserLog.filter(item=>!expectedHTTP.some(response=>item.url===origin+response.path && item.text.includes(String(response.status))));
  assert.deepEqual(unexpectedBrowserLog,[]);
  assert.deepEqual(unexpectedHTTP,[]);
  assert.deepEqual(errors,[]);
  const report={status:'PASS',measurements,pilotChecks,network,expectedHTTP,browserLog,errors,logoutGet,realCSRF:true,realCookies:true,sessionMocks:false,viewerPermissions:true};
  fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({status:report.status,screens:measurements.length,errors:errors.length,logoutGet,viewerPermissions:true}));
  await call('Browser.close');socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
