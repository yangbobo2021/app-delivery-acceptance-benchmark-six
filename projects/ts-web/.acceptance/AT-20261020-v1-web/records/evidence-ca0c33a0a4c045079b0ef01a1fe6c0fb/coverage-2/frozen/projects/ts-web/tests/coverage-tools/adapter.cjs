const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const {createCoverageMap}=require('istanbul-lib-coverage');
const {ROOT,SOURCES,hash,read,write,instrument,registration,nativeMap,components,snapshots}=require('./core.cjs');
const [operation,requestPath,responsePath]=process.argv.slice(2);
const versions=()=>[
 {name:'istanbul-lib-instrument',version:require('istanbul-lib-instrument/package.json').version,role:'Original JS/TS AST instrumentation and native zero-hit units'},
 {name:'istanbul-lib-coverage',version:require('istanbul-lib-coverage/package.json').version,role:'Native counters, merge and line/branch statistics'},
 {name:'@babel/core',version:require('@babel/core/package.json').version,role:'Compiler AST extraction of Istanbul registration for zero-runtime probes'},
 {name:'esbuild',version:require('../../node_modules/esbuild').version,role:'Strip TypeScript after original-source instrumentation'},
 {name:'Node.js',version:process.version,role:'Synchronous module hooks and inherited process lifecycle'}
];
function resolveMapped(p,mapping={},digest){
 if(fs.existsSync(p)&&(!digest||hash(p)===digest))return p;
 const v=mapping[p+'#'+digest]||mapping[p];
 if(v){const actual=typeof v==='string'?v:v.path; if(digest&&hash(actual)!==digest)throw Error('Mapped artifact hash mismatch: '+p);return actual;}
 return p;
}
function bound(p,digest,mapping){const actual=resolveMapped(p,mapping,digest);if(hash(actual)!==digest)throw Error('Frozen bytes changed: '+p);return actual;}
function profileAt(prepared,mapping={}){
 const p=prepared.endsWith('.json')?prepared:path.join(prepared,'prepared.json');
 return {path:p,profile:read(resolveMapped(p,mapping))};
}
function verify(profile,mapping={}){
 if(profile.schema!=='project-coverage-preparation-v1')throw Error('Invalid preparation schema');
 const spec=profile.spec;
 for(const [name,digest]of Object.entries({...spec.source_hashes,...profile.adapter_files}))bound(path.join(spec.project_root,name),digest,mapping);
 bound(spec.inventory_path,spec.inventory_sha256,mapping);
 const runtime=read(bound(spec.runtime_manifest,spec.runtime_sha256,mapping));
 const probes=read(bound(spec.probe_report,spec.probe_report_sha256,mapping));
 if(runtime.workspace!==spec.project_root||runtime.revision!==spec.revision||probes.runtime_sha256!==spec.runtime_sha256)throw Error('Runtime/probe preparation mismatch');
 if(probes.status!=='ready'||probes.workspace!==spec.project_root||probes.revision!==spec.revision)throw Error('Preparation routes have not all passed in this workspace and revision');
 if(!mapping||!Object.keys(mapping).length){
  for(const item of runtime.executables)bound(item.resolved_path,item.sha256,mapping);
  for(const [name,digest]of Object.entries(runtime.dependency_hashes))bound(path.join(spec.project_root,name),digest,mapping);
  const lock=read(path.join(__dirname,'package-lock.json'));
  for(const [name,item]of Object.entries(lock.packages||{})){
   if(name&&item.version&&read(path.join(__dirname,name,'package.json')).version!==item.version)throw Error('Installed coverage dependency differs from frozen lock: '+name);
  }
 }
 for(const tool of profile.tools){
  const actual=versions().find(t=>t.name===tool.name);
  if(actual&&actual.version!==tool.version)throw Error('Coverage tool version changed');
  if(tool.name==='Playwright'&&read(path.join(runtime.runtime_root,'browser-tools/node_modules/playwright/package.json')).version!==tool.version)throw Error('Browser coverage dependency changed');
 }
 for(const name of SOURCES)instrument(name,bound(path.join(spec.project_root,name),spec.source_hashes[name],mapping),spec.project_root); // Tool API smoke against the frozen or mapped source.
 return runtime;
}
function collection(raw){
 const all=fs.readdirSync(raw).sort();
 const starts=all.filter(n=>n.endsWith('.started.json'));
 const missing=starts.filter(n=>!all.includes(n.replace('.started.json','.ended.json')));
 const errors=all.filter(n=>n.includes('-capture-error-'));
 return {complete:starts.length>0&&!missing.length&&!errors.length,missing,errors};
}
function reportData(report,mapping){
 const files=report.raw_evidence.filter(x=>x.role==='istanbul-snapshot').map(x=>bound(x.path,x.sha256,mapping));
 for(const item of report.raw_evidence)bound(item.path,item.sha256,mapping);
 const lifecycle=read(bound(report.lifecycle.path,report.lifecycle.sha256,mapping));
 const recorded=report.raw_evidence.map(x=>path.basename(x.path));
 const starts=recorded.filter(n=>n.endsWith('.started.json'));
 const endingsValid=starts.length>0&&starts.every(n=>recorded.includes(n.replace('.started.json','.ended.json')))&&!recorded.some(n=>n.includes('-capture-error-'));
 if(lifecycle.complete&&(!endingsValid||lifecycle.signal||lifecycle.interrupted))throw Error('Lifecycle claims completion without native teardown records');
 return {map:nativeMap(files),complete:lifecycle.complete};
}
async function main(){
 if(operation==='startup-check'){
  const {createCoverageMap}=require('istanbul-lib-coverage');
  const baseline=instrument(SOURCES[0]).baseline;
  const noSnapshot=components(createCoverageMap({}),[SOURCES[0]])[0];
  const stopped=components(createCoverageMap({[baseline.path]:baseline}),[SOURCES[0]],false)[0];
  if(noSnapshot.line.status!=='unavailable'||stopped.line.status!=='incomplete')throw Error('Failure state propagation failed');
  for(const name of SOURCES){
   const generated=instrument(name);
   if(/new Function\(/.test(generated.code))throw Error('CSP-incompatible global registration');
   const context=require('node:vm').createContext({});
   require('node:vm').runInContext(registration(name),context);
   const summary=createCoverageMap(context.__coverage__).fileCoverageFor(generated.baseline.path).toSummary().toJSON();
   if(summary.lines.total<=0||summary.lines.covered!==0||summary.branches.covered!==0)throw Error('Generated runtime registration is not a real zero-count baseline');
  }
  const result={status:'valid',tools:versions(),failure_paths:{route_not_started:noSnapshot,missing_native_snapshot:noSnapshot,teardown_incomplete:stopped},note:'Synthetic baseline used only to validate incomplete status propagation; no business or collection probe executed'};
  write(requestPath,result);console.log(JSON.stringify({status:'valid',tools:result.tools}));return;
 }
 const request=read(requestPath),mapping=request.artifact_map||{};
 let result;
 if(operation==='verify-preparation'){
  const {profile}=profileAt(request.prepared,mapping);verify(profile,mapping);result={status:'valid'};
 }else if(operation==='run'){
  const {path:preparedPath,profile}=profileAt(request.prepared);bound(preparedPath,request.prepared_sha256);verify(profile);
  const raw=path.join(request.output,'native');fs.mkdirSync(raw,{recursive:true});
  const lifecycle=path.join(request.output,'collection-lifecycle.json');
  write(lifecycle,{complete:false,reason:'Execution started; collection teardown pending'});
  const env={...process.env,...request.env,PROJECT_COVERAGE_RAW:raw,PROJECT_COVERAGE_RUNTIME:profile.spec.runtime_manifest,NODE_OPTIONS:[request.env?.NODE_OPTIONS||process.env.NODE_OPTIONS||'',`--require=${path.join(__dirname,'preload.cjs')}`].join(' ').trim()};
  const child=spawn(request.command[0],request.command.slice(1),{cwd:request.cwd,env,stdio:'inherit',detached:true});
  let interrupted=false;
  const terminate=()=>{interrupted=true;try{process.kill(-child.pid,'SIGTERM');}catch{};setTimeout(()=>{try{process.kill(-child.pid,'SIGKILL');}catch{}},2000).unref();};
  process.once('SIGTERM',terminate);process.once('SIGINT',terminate);
  const [code,signal]=await once(child,'exit');
  // Drain descendants even if the test forgot its server. Forced or absent endings stay incomplete.
  try{process.kill(-child.pid,'SIGTERM');}catch(error){if(error.code!=='ESRCH')throw error;}
  for(let attempt=0;attempt<20&&!collection(raw).complete;attempt++)await new Promise(resolve=>setTimeout(resolve,50));
  const state=collection(raw);
  process.removeListener('SIGTERM',terminate);process.removeListener('SIGINT',terminate);
  write(lifecycle,{...state,complete:state.complete&&!signal&&!interrupted,exit_code:code,signal,interrupted,command:request.command});
  result={status:state.complete&&!signal&&!interrupted?'collected':'incomplete',exit_code:code,signal};write(responsePath,result);process.exitCode=interrupted?143:code??1;return;
 }else if(operation==='finish'){
  const session=read(request.request),receipt=read(request.receipt);
  const {profile}=profileAt(session.prepared);verify(profile);
  if(receipt.coverage_session_sha256!==hash(request.request))throw Error('Execution receipt does not bind session');
  const lifecyclePath=path.join(request.output,'collection-lifecycle.json');
  const lifecycle=read(lifecyclePath);const files=snapshots(path.join(request.output,'native'));
  const map=nativeMap(files),cs=components(map,SOURCES,lifecycle.complete);
  const raw=fs.readdirSync(path.join(request.output,'native')).sort().map(name=>path.join(request.output,'native',name));
  result={schema:'project-tool-coverage-report-v1',protocol:'project-coverage-v1',prepared:session.prepared,prepared_sha256:session.prepared_sha256,scene_id:session.scene_id,revision:profile.spec.revision,source_hashes:profile.spec.source_hashes,tools:profile.tools,collection_relation:'same_run',status:lifecycle.complete&&cs.every(c=>c.line.status==='measured')?'measured':'incomplete',receipt_path:request.receipt,execution_sha256:hash(request.receipt),raw_evidence:raw.map(p=>({path:p,sha256:hash(p),role:p.endsWith('.coverage.json')?'istanbul-snapshot':'lifecycle'})),lifecycle:{path:lifecyclePath,sha256:hash(lifecyclePath)},session:{path:request.request,sha256:hash(request.request)},components:cs};
  // Include lifecycle even if no collector process ever started: never fabricate a native baseline.
  result.raw_evidence.push({path:lifecyclePath,sha256:hash(lifecyclePath),role:'collection-lifecycle'});
 }else if(operation==='verify-report'){
  const report=read(resolveMapped(request.report,mapping));
  const {profile}=profileAt(report.prepared,mapping);verify(profile,mapping);
  bound(report.receipt_path,report.execution_sha256,mapping);bound(report.session.path,report.session.sha256,mapping);
  const data=reportData(report,mapping);
  const expected=components(data.map,SOURCES,data.complete,profile.spec.project_root);
  if(JSON.stringify(expected)!==JSON.stringify(report.components))throw Error('Native recomputation differs from report');
  const status=data.complete&&expected.every(c=>c.line.status==='measured')?'measured':'incomplete';
  if(report.status!==status)throw Error('Report completeness differs from raw lifecycle');
  result={status:'valid'};
 }else if(operation==='summarize'){
  const reports=request.reports.map(p=>read(resolveMapped(typeof p==='string'?p:p.path,mapping)));
  if(!reports.length)throw Error('No reports');
  const first=reports[0],map=createCoverageMap({});let complete=true;
  for(const report of reports){
   if(report.prepared_sha256!==first.prepared_sha256||report.revision!==first.revision||JSON.stringify(report.source_hashes)!==JSON.stringify(first.source_hashes))throw Error('Incompatible reports');
   const d=reportData(report,mapping);map.merge(d.map);complete=complete&&d.complete;
  }
  const {profile}=profileAt(first.prepared,mapping);
  const cs=components(map,SOURCES,complete,profile.spec.project_root);
  const scope={status:complete&&cs.every(c=>c.line.status==='measured')?'measured':'incomplete',components:cs};
  const inventory=read(bound(profile.spec.inventory_path,profile.spec.inventory_sha256,mapping));
  if(request.inventory){const actual=typeof request.inventory==='string'?request.inventory:request.inventory.path;if(actual&&hash(resolveMapped(actual,mapping))!==profile.spec.inventory_sha256)throw Error('Summary scope differs from frozen inventory');}
  const changed=inventory.changed_source_paths||[];
  const changedScope=changed.length?{status:'incomplete',reason:'Changed-file scope needs selected executable source support',components:components(map,SOURCES.filter(s=>changed.includes(s)),complete)}:{status:'unavailable',reason:inventory.basis||'No changed-file scope declared'};
  result={tools:first.tools,scopes:{project:scope,changed_files:changedScope,changed_lines:{status:'unavailable',reason:'Requirements-only baseline has no declared changed-line scope; project percentages are not substituted'}}};
 }else throw Error('Unknown coverage operation: '+operation);
 write(responsePath,result);
}
main().catch(error=>{console.error(error.stack);if(responsePath)write(responsePath,{status:'invalid',reason:error.message});process.exitCode=1;});
