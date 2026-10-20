const {app,BrowserWindow}=require('electron');const fs=require('node:fs'),path=require('node:path');
const raw=process.env.ACCEPTANCE_COVERAGE_RAW;if(!raw)throw Error('Missing ACCEPTANCE_COVERAGE_RAW');
let stopping=false,errors=[],windows=new Set();
const write=(name,value)=>{const p=path.join(raw,name+'.json');fs.writeFileSync(p+'.tmp',JSON.stringify(value));fs.renameSync(p+'.tmp',p);};
write('lifecycle-'+process.pid,{complete:false,pid:process.pid,mode:process.env.ACCEPTANCE_COVERAGE_MODE||'actual'});
app.on('web-contents-created',(_,wc)=>{wc.on('console-message',(_event,...args)=>{
 const message=typeof _event.message==='string'?_event.message:(args.find(x=>x&&typeof x==='object'&&typeof x.message==='string')?.message||args.find(x=>typeof x==='string'&&x.startsWith('__ACCEPTANCE_COV__')));
 if(!message?.startsWith('__ACCEPTANCE_COV__'))return;
 try{const data=JSON.parse(message.slice('__ACCEPTANCE_COV__'.length));write('snapshot-'+data.token,data);}catch(e){errors.push(String(e));}
 });});
async function flush(w){for(const world of [0,999]){try{const ok=await w.webContents.executeJavaScriptInIsolatedWorld(world,[{code:'typeof globalThis.__acceptanceFlush==="function" && (globalThis.__acceptanceFlush(), true)'}]);if(!ok)errors.push('Missing publisher in world '+world);}catch(e){errors.push(String(e));}}}
app.on('browser-window-created',(_,w)=>{windows.add(w);w.on('closed',()=>windows.delete(w));let closing=false;w.on('close',event=>{if(closing||stopping)return;event.preventDefault();flush(w).finally(()=>{closing=true;w.close();});});});
app.on('before-quit',event=>{if(stopping)return;event.preventDefault();stopping=true;(async()=>{
 for(const w of windows)await flush(w);
 write('snapshot-main-'+process.pid,{coverage:globalThis.__coverage__||{}});
 write('lifecycle-'+process.pid,{complete:errors.length===0,errors,pid:process.pid,mode:process.env.ACCEPTANCE_COVERAGE_MODE||'actual'});app.quit();
 })().catch(e=>{write('lifecycle-'+process.pid,{complete:false,errors:[String(e)]});app.exit(1);});});
if(process.env.ACCEPTANCE_COVERAGE_MODE==='zero'){
 require('./main.js');app.whenReady().then(()=>{const w=new BrowserWindow({show:false,webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});w.loadFile(path.join(__dirname,'index.html'));});
}else require('./main.js');
// Probe mode only: no clicks, notes mutation, or business assertions.
if(process.env.ACCEPTANCE_COVERAGE_PROBE==='1')app.whenReady().then(()=>{let reloaded=false;const timer=setInterval(()=>{const names=fs.readdirSync(raw).filter(x=>x.startsWith('snapshot-'));if(names.length>=2&&!reloaded){reloaded=true;for(const w of windows)w.webContents.reload();}else if(reloaded&&names.length>=4){clearInterval(timer);setTimeout(()=>app.quit(),200);}},100);setTimeout(()=>{clearInterval(timer);errors.push('Probe navigation snapshot deadline');app.quit();},15000).unref();});
setInterval(()=>{if(!stopping&&fs.existsSync(path.join(raw,'stop.json')))app.quit();},100);
