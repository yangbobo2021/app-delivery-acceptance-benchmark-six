const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {spawn,spawnSync}=require('node:child_process');
const {once}=require('node:events');
const {ROOT,SOURCES,read,write,registration,snapshots,nativeMap,components}=require('./core.cjs');
const [operation,route,mode,raw,runtimePath]=process.argv.slice(2);
const names=route==='browser'?[SOURCES[1]]:route==='build'?[SOURCES[2]]:[SOURCES[0]];
async function main(){
 if(operation==='read'){
  const c=components(nativeMap(snapshots(raw)),names);
  console.log(JSON.stringify({schema:'coverage-probe-normalized-v1',components:c.map(x=>({id:x.id,source_paths:x.source_paths,metrics:{line:x.line,branch:x.branch}}))}));return;
 }
 if(operation!=='collect')throw Error('Unknown probe operation');
 const runtime=read(runtimePath);
 process.env.PLAYWRIGHT_BROWSERS_PATH=path.join(runtime.runtime_root,'playwright-browsers');
 const env={...process.env,PROJECT_COVERAGE_RAW:raw,PROJECT_COVERAGE_RUNTIME:runtimePath,NODE_OPTIONS:`--require=${path.join(__dirname,'preload.cjs')}`,PORT:'0'};
 let server,browser;
 try{
  if(mode==='zero'){
   if(route==='browser'){
    const {chromium}=require(path.join(runtime.runtime_root,'browser-tools/node_modules/playwright'));
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage();
    await page.addScriptTag({content:registration(names[0])});
    write(path.join(raw,'zero.coverage.json'),await page.evaluate(()=>globalThis.__coverage__));
   }else{
    const context=vm.createContext({});
    vm.runInContext(registration(names[0]),context);
    write(path.join(raw,'zero.coverage.json'),context.__coverage__);
   }
  }else if(route==='build'){
   const result=spawnSync(process.execPath,['build.mjs'],{cwd:path.join(ROOT,'projects/ts-web'),env,encoding:'utf8'});
   if(result.status!==0)throw Error(result.stderr);
  }else{
   server=spawn(process.execPath,['server.mjs','0'],{cwd:path.join(ROOT,'projects/ts-web'),env,stdio:['ignore','pipe','inherit']});
   const startup=await Promise.race([once(server.stdout,'data'),new Promise((_,reject)=>setTimeout(()=>reject(Error('Server startup timed out')),12000).unref())]);
   const port=JSON.parse(startup[0].toString().trim()).port;
   const url='http://127.0.0.1:'+port+'/';
   if(route==='browser'){
    // Load the same lifecycle adapter used by formal run; no business interactions.
    Object.assign(process.env,env);
    require('./preload.cjs');
    const {chromium}=require(path.join(runtime.runtime_root,'browser-tools/node_modules/playwright'));
    browser=await chromium.launch({headless:true});
    const context=await browser.newContext();
    const page=await context.newPage();
    await page.goto(url);await page.reload();await context.close();
   }else{
    const response=await fetch(url);if(!response.ok)throw Error('Server resource unavailable');await response.arrayBuffer();
   }
  }
 }finally{
  if(browser)await browser.close();
  if(server&&server.exitCode===null){const stopped=once(server,'exit');server.kill('SIGTERM');await stopped;}
 }
 write(path.join(raw,'probe-lifecycle.json'),{route,mode,status:'complete',zero_mode:mode==='zero'?'Runtime executed only Istanbul-generated registration function; product statements not executed':null});
 // Failure paths use the real snapshot just collected, without modifying it or
 // inventing counts. Evidence lives outside the host's read-only raw directory.
 const {createCoverageMap}=require('istanbul-lib-coverage');
 const absent=components(createCoverageMap({}),names);
 const unfinished=components(nativeMap(snapshots(raw)),names,false);
 if(absent.some(c=>c.line.status!=='unavailable'||c.branch.status!=='unavailable')||unfinished.some(c=>c.line.status!=='incomplete'))throw Error('Failure propagation rejected');
 write(path.join(path.dirname(raw),'failure-path-evidence.json'),{schema:'project-coverage-failure-path-check-v1',status:'valid',cases:[{id:'route-not-started',native_snapshots:[],components:absent},{id:'native-snapshot-missing',native_snapshots:[],components:absent},{id:'teardown-not-completed',native_snapshots:snapshots(raw).map(p=>({path:p,sha256:require('./core.cjs').hash(p)})),collection_complete:false,components:unfinished}],note:'State injection checks using the same project normalization as finish; no business execution or zero baseline substitution'});
}
main().catch(error=>{console.error(error);process.exitCode=1;});
