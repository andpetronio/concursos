// Real HTTP QA against a disposable Django server and an isolated Chrome profile.
// No request interception, HTML fixture or session mocks.
// Usage: node core/tests/detail_tabs.browser.test.js <CDP URL> <QA origin> <output dir>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const [endpoint, origin, output] = process.argv.slice(2);
const screenshots = path.resolve('docs/evidencias/sdd-006/3a/correccion-tabs');
fs.mkdirSync(screenshots,{recursive:true});
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
  const requestURLs = new Map();
  const networkFailures = [];
  const intentionalFailures = [];
  const browserLog = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id); pending.delete(message.id);
      if (message.error) request.reject(Error(JSON.stringify(message.error))); else request.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
      const deliberate = message.params.args.some(arg => arg.description?.includes('QA deliberate initializer failure'));
      if (deliberate) intentionalFailures.push({kind:'initializer',message:message.params.args[0]?.value});
      else errors.push('console.error: '+message.params.args[0]?.value);
    }
    else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') browserLog.push({url:message.params.entry.url,text:message.params.entry.text});
    else if (message.method === 'Network.loadingFailed' && !message.params.canceled) {
      const failure={url:requestURLs.get(message.params.requestId),...message.params};
      networkFailures.push(failure);
      if (failure.blockedReason === 'inspector' && failure.url?.endsWith('/js/detail-tabs.js')) intentionalFailures.push({kind:'script-block',...failure});
      else errors.push(JSON.stringify(failure));
    }
    else if (message.method === 'Network.responseReceived') {
      const response = message.params.response;
      if (response.url.startsWith(origin)) network.push({path:new URL(response.url).pathname,method:requestMethods.get(message.params.requestId),status:response.status});
    } else if (message.method === 'Network.requestWillBeSent') {
      const response = message.params.redirectResponse;
      if (response?.url.startsWith(origin)) network.push({path:new URL(response.url).pathname,method:requestMethods.get(message.params.requestId),redirectStatus:response.status});
      requestMethods.set(message.params.requestId,message.params.request.method);
      requestURLs.set(message.params.requestId,message.params.request.url);
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
  const navigate = async path => {
    const url = new URL(path, origin);
    await call('Page.navigate', {url: url.href});
    await waitPage(url.pathname);
    assert.equal(await evaluate('location.search'), url.search);
    assert.equal(await evaluate('location.hash'), url.hash);
  };
  const reload = async () => {
    const pathname = await evaluate('location.pathname');
    const loaded = new Promise(resolve => {
      const listener = event => {
        if (JSON.parse(event.data).method === 'Page.loadEventFired') {
          socket.removeEventListener('message', listener);
          resolve();
        }
      };
      socket.addEventListener('message', listener);
    });
    await call('Page.reload');
    await loaded;
    await waitPage(pathname);
  };
  const resize = async width => {await call('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});await pause();};
  const key = async key => {await call('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:({Tab:9,Escape:27,ArrowRight:39,ArrowLeft:37,Home:36,End:35,Enter:13,' ':32}[key])});await call('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});await pause();};
  const capture = async name => {const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(screenshots,name+'.png'),Buffer.from(shot.data,'base64'));};
  const login = async username => {
    await navigate('/ingresar/');
    await evaluate(`document.querySelector('#id_username').value=${JSON.stringify(username)};document.querySelector('#id_password').value='Synthetic-Only-2026!';document.querySelector('form').requestSubmit()`);
    await waitPage('/');
    assert.equal(await evaluate(`document.querySelector('.account-name').textContent`),username);
  };
  await Promise.all([call('Page.enable'),call('Runtime.enable'),call('Network.enable'),call('Log.enable')]);
  await call('Network.setCacheDisabled',{cacheDisabled:true});
  await call('Network.clearBrowserCookies');
  await resize(1440); await login('operador_qa');
  const ready=JSON.parse(fs.readFileSync(path.join(output,'ready.json'),'utf8'));
  const sections=['resumen','datos-concurso','jurados','veedores','aspirantes','control-documental','documentos','historial'];
  const activate=async id=>{await evaluate(`document.querySelector('[data-detail-tab-navigation] a[href="#${id}"]').click()`);await pause();};
  const state=()=>evaluate(`(() => {const root=document.querySelector('[data-detail-tabs]'),nav=root.querySelector('[role=tablist]');return {width:innerWidth,pageWidth:document.documentElement.scrollWidth,visible:[...root.querySelectorAll('[role=tabpanel]')].filter(p=>!p.hidden).map(p=>p.id),selected:nav?.querySelector('[aria-selected=true]')?.hash,roving:nav?.querySelectorAll('[tabindex="0"]').length,hash:location.hash,navBox:nav?.getBoundingClientRect().toJSON(),selectedBox:nav?.querySelector('[aria-selected=true]')?.getBoundingClientRect().toJSON(),hint:root.querySelector('[data-detail-tabs-help]').textContent,hintVisible:!root.querySelector('[data-detail-tabs-help]').hidden,focus:document.activeElement.id};})()`);
  const tabChecks=[];
  for(const width of [1440,1280,768,360]) {
    await resize(width);await navigate(ready.detail);
    for(const section of sections) {
      await activate(section);
      const result=await state();
      assert.equal(result.width,width);assert(result.pageWidth<=width,JSON.stringify(result));
      assert.deepEqual(result.visible,[`panel-${section}`]);assert.equal(result.roving,1);assert.equal(result.selected,`#${section}`);
      assert(result.navBox.x>=0 && result.navBox.right<=width+1);
      assert(result.selectedBox.left>=result.navBox.left-1 && result.selectedBox.right<=result.navBox.right+1, 'Selected tab must be fully visible');
      assert.equal(await evaluate(`getComputedStyle(document.querySelector('[aria-selected=true]')).borderBottomStyle`),'solid');
      tabChecks.push({section,...result});
      if(section==='resumen'||section==='jurados')await capture(`${section}-${width}`);
    }
    if(width===360) {
      assert((await state()).hintVisible);
      await capture('historial-movil-indicador');
      await activate('jurados');
      await evaluate(`const r=document.querySelector('#jurados .table-region');r.scrollLeft=r.scrollWidth`);
      await capture('jurados-acciones-360');
    }
    await activate('jurados');
    const actions=await evaluate(`Array.from(document.querySelectorAll('#jurados .participation-actions'),row=>({direction:getComputedStyle(row).flexDirection,links:Array.from(row.children,a=>({height:a.getBoundingClientRect().height,width:a.getBoundingClientRect().width,box:a.getBoundingClientRect().toJSON(),button:a.classList.contains('button')}))}))`);
    for(const action of actions){assert.equal(action.direction,'row');assert(action.links.every(a=>a.height>=44&&a.button));if(width>760)assert(action.links[1].box.left>=action.links[0].box.right-1);}
  }
  await resize(1280);await navigate(ready.detail);
  await activate('jurados');await activate('aspirantes');
  await evaluate('history.back()');await pause();assert.equal((await state()).selected,'#jurados');
  await evaluate('history.forward()');await pause();assert.equal((await state()).selected,'#aspirantes');
  await reload();assert.equal((await state()).selected,'#aspirantes');
  await evaluate(`document.querySelector('[data-detail-tab-navigation] a[href="#jurados"]').focus()`);
  await key('ArrowRight');assert.equal(await evaluate('document.activeElement.hash'),'#veedores');assert.equal((await state()).selected,'#aspirantes');
  await key(' ');assert.equal((await state()).selected,'#veedores');
  await key('Home');assert.equal(await evaluate('document.activeElement.hash'),'#resumen');
  await key('End');assert.equal(await evaluate('document.activeElement.hash'),'#historial');
  await key('Enter');assert.equal((await state()).selected,'#historial');
  await key('Tab');assert.equal(await evaluate('document.activeElement.id'),'panel-historial');
  await navigate(ready.detail+'#not-a-section');assert.equal((await state()).selected,'#resumen');
  await navigate(ready.detail+'#%E0%A4%A');assert.equal((await state()).selected,'#resumen');
  // Every existing descendant fragment selects its owning tab, not just section IDs.
  await navigate(ready.detail);
  const control=await evaluate(`(() => {const f=[...document.querySelectorAll('.document-control form')].find(f=>f.querySelector('[name$="fojas"]'));return {action:f.getAttribute('action'),id:f.closest('.document-control').id,fojas:f.querySelector('[name$="fojas"]').value,observaciones:f.querySelector('textarea').value};})()`);
  await navigate(ready.detail+'#'+control.id);assert.equal((await state()).selected,'#control-documental');
  await reload();assert.equal((await state()).selected,'#control-documental');assert.equal((await state()).hash,'#'+control.id);
  await evaluate(`document.querySelector('form[action=${JSON.stringify(control.action)}]').requestSubmit()`);await waitPage(ready.detail);
  assert.equal((await state()).selected,'#control-documental');assert.equal((await state()).hash,'#'+control.id);await capture('control-retorno-1280');
  // Browser values survive switching tabs: no cloned forms or AJAX save.
  await evaluate(`document.querySelector('form[action=${JSON.stringify(control.action)}] textarea').value='Texto sin guardar conservado al cambiar pestaña'`);
  await activate('jurados');await activate('control-documental');
  assert.equal(await evaluate(`document.querySelector('form[action=${JSON.stringify(control.action)}] textarea').value`),'Texto sin guardar conservado al cambiar pestaña');
  await evaluate(`(() => {const f=document.querySelector('form[action=${JSON.stringify(control.action)}]');f.querySelector('[name$="fojas"]').value='9/2';f.noValidate=true;f.requestSubmit();})()`);
  await waitPage(control.action.split('#')[0]);
  assert.equal((await state()).selected,'#control-documental');
  assert.equal(await evaluate(`document.querySelector('.field-errors').closest('form').querySelector('[name$="fojas"]').value`),'9/2');
  assert.equal(await evaluate(`document.querySelector('.field-errors').closest('form').querySelector('textarea').value`),'Texto sin guardar conservado al cambiar pestaña');
  await capture('control-error-1280');
  // Rendered errors win over a stale hash from another tab on initial load.
  await call('Page.addScriptToEvaluateOnNewDocument',{source:"if(location.pathname.includes('/control-documental/'))history.replaceState(null,'',location.pathname+'#jurados')"});
  await evaluate(`(() => {const f=document.querySelector('.field-errors').closest('form');f.noValidate=true;f.requestSubmit();})()`);await waitPage(control.action.split('#')[0]);
  assert.equal((await state()).selected,'#control-documental');assert.equal((await state()).hash,'#'+control.id);
  await resize(360);
  const resized=await state();assert(resized.selectedBox.left>=resized.navBox.left-1 && resized.selectedBox.right<=resized.navBox.right+1);
  await capture('control-error-360');
  // Direct edit GET -> POST, without first visiting/selecting its tab.
  await resize(1280);await navigate(ready.detail);
  const persistence=[];
  let correction;
  for(const [section,kind] of [['jurados','jurado'],['veedores','veedor'],['aspirantes','aspirante']]) {
    const edit=await evaluate(`document.querySelector('#${section} .participation-edit').getAttribute('href')`);
    await navigate(edit);
    await evaluate(`document.querySelector('#id_email').value='${kind}.tabs@example.invalid';document.querySelector('main form').requestSubmit()`);await waitPage(ready.detail);
    assert.equal((await state()).selected,'#'+section);assert.equal((await state()).hash,'#'+section);
    assert(await evaluate(`document.getElementById('${section}').textContent.includes('${kind}.tabs@example.invalid')`));
    await reload();assert.equal((await state()).selected,'#'+section);
    persistence.push({kind,fragment:'#'+section,post:true,persisted:true});
    if(kind==='aspirante')correction=await evaluate(`document.querySelector('#aspirantes .participation-correct').getAttribute('href')`);
  }
  await capture('aspirante-retorno-1280');
  await navigate(correction);await evaluate(`document.querySelector('#id_nombre').value='María de prueba';document.querySelector('main form').requestSubmit()`);await waitPage(ready.detail);
  assert.equal((await state()).selected,'#aspirantes');assert(await evaluate(`document.querySelector('#aspirantes').textContent.includes('María de prueba')`));
  // JS disabled: all sections + normal links + a real POST with a contextual fragment.
  await call('Emulation.setScriptExecutionDisabled',{value:true});await navigate(ready.detail+'#'+control.id);await reload();
  assert.equal(await evaluate(`document.querySelectorAll('[role=tab]').length`),0);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('[data-detail-panel]')).filter(e=>e.getClientRects().length).length`),8);
  await capture('sin-javascript-1280');
  await evaluate(`document.querySelector('form[action=${JSON.stringify(control.action)}]').requestSubmit()`);await waitPage(ready.detail);
  assert.equal(await evaluate('location.hash'),'#'+control.id);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('[data-detail-panel]')).filter(e=>e.getClientRects().length).length`),8);
  await call('Emulation.setScriptExecutionDisabled',{value:false});
  // A script load failure also leaves the entire server response available.
  await call('Network.setBlockedURLs',{urls:['*detail-tabs.js']});await navigate(ready.detail);await reload();
  assert.equal(await evaluate(`document.querySelectorAll('[role=tab]').length`),0);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('[data-detail-panel]')).filter(e=>e.getClientRects().length).length`),8);
  await call('Network.setBlockedURLs',{urls:[]});await navigate(ready.detail);await reload();
  // An initializer exception rolls back partial enhancement to accessible HTML.
  const failedInit=await call('Page.addScriptToEvaluateOnNewDocument',{source:`const NativeObserver=window.ResizeObserver;window.ResizeObserver=class extends NativeObserver {observe(target,...args){if(target.matches('[data-detail-tab-navigation]'))throw Error('QA deliberate initializer failure');return super.observe(target,...args);}};`});
  await reload();
  assert.equal(await evaluate(`document.querySelectorAll('[role=tab]').length`),0);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('[data-detail-panel]')).filter(e=>e.getClientRects().length).length`),8);
  await call('Page.removeScriptToEvaluateOnNewDocument',{identifier:failedInit.identifier});await reload();
  await evaluate(`document.querySelector('form[action="/salir/"]').requestSubmit()`);await waitPage('/ingresar/');await login('lector_qa');await navigate(ready.detail);
  assert(await evaluate(`!document.querySelector('.participation-actions') && !document.querySelector('form[action*="control-documental"]')`));
  for(const section of sections){await activate(section);assert.equal((await state()).selected,'#'+section);}
  await resize(360);await activate('aspirantes');await capture('lector-aspirantes-360');
  const denied=await evaluate(`fetch(${JSON.stringify(correction)},{method:'POST',headers:{'X-CSRFToken':document.querySelector('form[action="/salir/"] input[name=csrfmiddlewaretoken]').value},body:new URLSearchParams({nombre:'No guardar'})}).then(r=>r.status)`);assert.equal(denied,403);
  const exceptions=errors;assert.deepEqual(exceptions,[]);
  assert.equal(intentionalFailures.filter(e=>e.kind==='initializer').length,1);
  assert(intentionalFailures.some(e=>e.kind==='script-block'));
  const unexpectedHTTP=network.filter(x=>x.status>=400&&!(x.status===403&&x.path===new URL(correction,origin).pathname)&&!(x.status===429&&x.path==='/sesion/actividad/')&&!(x.status===404&&x.path==='/favicon.ico'));assert.deepEqual(unexpectedHTTP,[]);
  const report={status:'PASS',widths:[1440,1280,768,360],tabChecks,manualKeyboard:true,historyRefresh:true,unknownHashFallback:true,individualControlHash:true,controlPOST:true,controlErrorsVisible:true,unsavedValuesPreserved:true,persistence,personCorrectionReturn:true,noJSAllVisibleAndPOST:true,scriptLoadFailureFallback:true,initializerFailureFallback:true,resizedActiveTabVisible:true,viewerDenied:denied,realHTTP:true,realCSRF:true,realCookies:true,network,networkFailures,intentionalFailures,errors,browserLog};
  fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({status:'PASS',widths:report.widths,tabChecks:tabChecks.length,persistence,noJS:true,errors:exceptions}));
  await call('Browser.close');socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
