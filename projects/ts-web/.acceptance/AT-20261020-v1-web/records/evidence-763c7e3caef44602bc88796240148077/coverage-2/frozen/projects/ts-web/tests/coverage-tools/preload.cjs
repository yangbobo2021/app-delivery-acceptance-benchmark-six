// Test-only process and browser lifecycle adapter. No product files are rewritten.
const fs=require('node:fs');
const path=require('node:path');
const {registerHooks}=require('node:module');
const {fileURLToPath}=require('node:url');
const {ROOT,SOURCES,instrument,write,read}=require('./core.cjs');
const raw=process.env.PROJECT_COVERAGE_RAW;
if(raw){
 const token=`node-${process.pid}`;
 write(path.join(raw,token+'.started.json'),{pid:process.pid});
 let sourceLoaded=false;
 registerHooks({load(url,context,next){
  const result=next(url,context);
  if(url.startsWith('file:')){
   const name=path.relative(ROOT,fileURLToPath(url));
   if(SOURCES.includes(name)&&!name.endsWith('.ts')){sourceLoaded=true;return {...result,source:instrument(name).code};}
  }
  return result;
 }});
 const flush=()=>{if(global.__coverage__&&Object.keys(global.__coverage__).length)write(path.join(raw,token+'.coverage.json'),global.__coverage__);};
 process.on('exit',code=>{flush();write(path.join(raw,token+'.ended.json'),{pid:process.pid,code,sourceLoaded});});
 // SIGTERM is the normal server cleanup used by the existing runtime smoke.
 process.on('SIGTERM',()=>{flush();process.exit(143);});
 const runtime=read(process.env.PROJECT_COVERAGE_RUNTIME);
 const playwright=require(path.join(runtime.runtime_root,'browser-tools/node_modules/playwright'));
 for(const kind of ['chromium']){
  const type=playwright[kind];
  const launch=type.launch.bind(type);
  type.launch=async(...args)=>{
   const browser=await launch(...args);const contexts=new Set();
   const newContext=browser.newContext.bind(browser);
   browser.newContext=async(...args)=>{
    const context=await newContext(...args);contexts.add(context);
    const contextToken=token+'-browser-context-'+require('node:crypto').randomUUID();
    write(path.join(raw,contextToken+'.started.json'),{pid:process.pid,route:'browser-context'});
    const pages=new Map();let serial=0;let contextClosing=false;
    const save=(id,cov)=>{if(cov&&Object.keys(cov).length)write(path.join(raw,`${token}-browser-${id}.coverage.json`),cov);};
    await context.exposeBinding('__acceptanceCoverageSnapshot',({page},id,cov)=>save(pages.get(page)+'-'+id,cov));
    await context.addInitScript(()=>{
     const id=Date.now()+'-'+Math.random();
     window.__acceptanceDocumentId=id;
     addEventListener('pagehide',()=>{if(globalThis.__coverage__)globalThis.__acceptanceCoverageSnapshot(id,globalThis.__coverage__);});
    });
    await context.route('**/app.js',async route=>{
     const original=await route.fetch();
     if(original.ok()) await route.fulfill({response:original,body:instrument('projects/ts-web/src/app.ts').code});
     else await route.fulfill({response:original});
    });
    async function capture(page){
     if(page.isClosed())return;
     try{const data=await page.evaluate(()=>({id:window.__acceptanceDocumentId,cov:globalThis.__coverage__}));save(pages.get(page)+'-'+data.id,data.cov);}
     catch(error){write(path.join(raw,token+'-capture-error-'+Date.now()+'.json'),{error:String(error)});throw error;}
    }
    context.on('page',page=>{
     pages.set(page,++serial);
     let managedClose=false;
     page.on('crash',()=>write(path.join(raw,token+'-capture-error-crash-'+Date.now()+'.json'),{error:'Browser page crashed before reliable teardown'}));
     page.on('close',()=>{if(!managedClose&&!contextClosing)write(path.join(raw,token+'-capture-error-unmanaged-close-'+Date.now()+'.json'),{error:'Page closed outside the managed flush lifecycle'});});
     for(const method of ['goto','reload','goBack','goForward','close']){
      const original=page[method].bind(page);
      page[method]=async(...args)=>{await capture(page);if(method==='close')managedClose=true;return original(...args);};
     }
    });
    const close=context.close.bind(context);
    context.close=async(...args)=>{await Promise.all(context.pages().map(capture));contextClosing=true;await close(...args);contexts.delete(context);write(path.join(raw,contextToken+'.ended.json'),{complete:true});};
    return context;
   };
   const close=browser.close.bind(browser);
   browser.close=async(...args)=>{for(const context of [...contexts])await context.close();return close(...args);};
   return browser;
  };
 }
}
