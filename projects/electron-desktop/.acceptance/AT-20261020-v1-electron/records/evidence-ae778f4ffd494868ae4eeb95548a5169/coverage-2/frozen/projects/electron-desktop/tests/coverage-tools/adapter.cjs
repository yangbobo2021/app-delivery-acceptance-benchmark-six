const c=require('./core.cjs');const {spawn}=require('node:child_process');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
function resolveBound(p,digest,mapping={}){if(c.fs.existsSync(p)&&(!digest||c.hash(p)===digest))return p;const a=mapping[p+'#'+digest]||mapping[p];const target=typeof a==='string'?a:a?.path;if(!target||digest&&c.hash(target)!==digest)throw Error('Missing or changed artifact: '+p);return target;}
function bound(p,digest,mapping){const actual=resolveBound(p,digest,mapping);if(digest&&c.hash(actual)!==digest)throw Error('Hash changed '+p);return actual;}
function profilePath(value){return value.endsWith('.json')?value:c.path.join(value,'prepared.json');}
function validate(p,mapping={}){
 if(p.schema!=='project-coverage-preparation-v1')throw Error('Wrong preparation schema');const s=p.spec;
 for(const [field,digest]of [['runtime_manifest','runtime_sha256'],['probe_report','probe_report_sha256'],['inventory_path','inventory_sha256']])bound(s[field],s[digest],mapping);
 const runtime=c.read(resolveBound(s.runtime_manifest,s.runtime_sha256,mapping));if(runtime.workspace!==s.project_root||runtime.revision!==s.revision)throw Error('Runtime identity mismatch');
 for(const [name,digest]of Object.entries({...s.source_hashes,...p.adapter_files}))bound(c.path.join(s.project_root,name),digest,mapping);
 for(const item of p.preparation_evidence)bound(item.path,item.sha256,mapping);
 if(JSON.stringify(p.tools)!==JSON.stringify(c.tools()))throw Error('Coverage tool versions changed');
 if(!Object.keys(mapping).length){for(const item of runtime.executables)bound(item.resolved_path,item.sha256);for(const [name,digest]of Object.entries(runtime.dependency_hashes))bound(c.path.join(s.project_root,name),digest);}
 return p;
}
function lifecycle(raw){const files=c.fs.existsSync(raw)?c.fs.readdirSync(raw).filter(n=>/^lifecycle.*\.json$/.test(n)):[];return {complete:files.length>0&&files.every(n=>c.read(c.path.join(raw,n)).complete),routes:files};}
function components(normal){return normal.components.map(x=>({id:x.id,label:c.path.basename(x.id),source_paths:x.source_paths,...x.metrics}));}
async function reportData(report,mapping={}){
 const p=c.read(bound(profilePath(report.prepared),report.prepared_sha256,mapping));validate(p,mapping);
 const raw=report.raw_evidence.map(a=>({original:a.path,actual:bound(a.path,a.sha256,mapping)}));
 const native=raw.filter(a=>/^snapshot-.*\.json$/.test(c.path.basename(a.original))).map(a=>a.actual);
 const lives=raw.filter(a=>/^lifecycle.*\.json$/.test(c.path.basename(a.original)));const complete=lives.length>0&&lives.every(a=>c.read(a.actual).complete);
 const normalized=await c.normalized(native,{complete});const cs=components(normalized);const status=complete&&cs.every(x=>x.line.status==='measured'&&x.branch.status==='measured')&&!Object.values(p.source_dispositions).some(x=>x.kind==='unsupported')?'measured':'incomplete';
 return {p,cs,status,native};
}
(async()=>{const [op,reqPath,response]=process.argv.slice(2);
 if(op==='selfcheck'){
 const instrument=require('istanbul-lib-instrument').createInstrumenter();instrument.instrumentSync('function untouched(){return 1;}','capability.js');const coverage=c.createCoverageMap({'capability.js':instrument.lastFileCoverage()});const mapped=await c.createSourceMapStore().transformCoverage(coverage);const summary=mapped.getCoverageSummary().toJSON();if(summary.lines.total<=0||summary.lines.covered!==0)throw Error('Istanbul API selfcheck failed');console.log(JSON.stringify({status:'valid',tools:c.tools(),note:'API startup only; host probes not executed'}));return;
 }
 const request=c.read(reqPath),mapping=request.artifact_map||{};let result;
 if(op==='verify-preparation'){
 const p=validate(c.read(resolveBound(request.prepared,null,mapping)),mapping);const probes=c.read(bound(p.spec.probe_report,p.spec.probe_report_sha256,mapping));if(!['ready','partial'].includes(probes.status))throw Error('Unusable probe report');result={status:'valid'};
 }else if(op==='run'){
 const prepared=profilePath(request.prepared);const p=validate(c.read(bound(prepared,request.prepared_sha256,mapping)),mapping);const raw=c.path.join(request.output,'native');c.fs.mkdirSync(raw,{recursive:true});const app=await c.build(c.path.join(request.output,'instrumented'));
 c.save(c.path.join(raw,'run-context.json'),{request:reqPath,request_sha256:c.hash(reqPath),scene_id:request.scene_id,command:request.command,prepared_sha256:request.prepared_sha256});
 const env={...process.env,...request.env,ACCEPTANCE_COVERAGE_RAW:raw,ACCEPTANCE_ELECTRON_APP:app};delete env.ACCEPTANCE_COVERAGE_MODE;delete env.ACCEPTANCE_COVERAGE_PROBE;
 const child=spawn(request.command[0],request.command.slice(1),{cwd:request.cwd,env,stdio:'inherit'});const outcome=await new Promise((res,rej)=>{child.on('error',rej);child.on('close',(code,signal)=>res({code,signal}))});
 c.save(c.path.join(raw,'stop.json'),{stop:true});for(let i=0;i<50&&!lifecycle(raw).complete;i++)await delay(100);
 const state=lifecycle(raw);if(!state.complete){for(const name of state.routes){const item=c.read(c.path.join(raw,name));if(!item.complete&&Number.isInteger(item.pid)){try{process.kill(-item.pid,'SIGKILL');}catch{try{process.kill(item.pid,'SIGKILL');}catch{}}}}}c.save(c.path.join(raw,'collection.json'),{complete:state.complete,command_exit:outcome,reason:state.complete?null:'No completed Electron collector lifecycle; missing snapshots remain unavailable'});
 result={status:state.complete?'collected':'incomplete',exit_code:outcome.code??1,signal:outcome.signal,raw};c.save(response,result);process.exitCode=outcome.code??1;return;
 }else if(op==='finish'){
 const session=c.read(request.request),receipt=c.read(request.receipt);const p=validate(c.read(bound(profilePath(session.prepared),session.prepared_sha256,mapping)),mapping);const raw=c.path.join(session.output,'native');
 const names=c.fs.readdirSync(raw).filter(n=>n.endsWith('.json'));const evidence=names.map(n=>({path:c.path.join(raw,n),sha256:c.hash(c.path.join(raw,n))}));
 const report={schema:'project-tool-coverage-report-v1',protocol:'project-coverage-v1',prepared:session.prepared,prepared_sha256:session.prepared_sha256,scene_id:session.scene_id,revision:p.spec.revision,source_hashes:p.spec.source_hashes,tools:p.tools,collection_relation:'same_run',receipt_path:request.receipt,execution_sha256:c.hash(request.receipt),raw_evidence:evidence,execution_request:{path:request.request,sha256:c.hash(request.request)}};
 const data=await reportData(report,mapping);report.status=data.status;report.components=data.cs;result=report;
 }else if(op==='verify-report'){
 const report=c.read(resolveBound(request.report,null,mapping));const data=await reportData(report,mapping);bound(report.receipt_path,report.execution_sha256,mapping);bound(report.execution_request.path,report.execution_request.sha256,mapping);
 if(JSON.stringify(data.cs)!==JSON.stringify(report.components)||data.status!==report.status)throw Error('Native recomputation disagrees');result={status:'valid'};
 }else if(op==='summarize'){
 if(!request.reports.length)throw Error('No reports');const reports=request.reports.map(p=>c.read(resolveBound(p,null,mapping)));if(reports.some(r=>r.prepared_sha256!==reports[0].prepared_sha256))throw Error('Incompatible preparations');
 const all=new Set();let incomplete=false,finalized=true,p;for(const report of reports){const data=await reportData(report,mapping);p=data.p;data.native.forEach(n=>all.add(n));incomplete ||= data.status!=='measured';finalized &&= data.cs.every(x=>x.line.status==='measured'&&x.branch.status==='measured');}
 const inventory=c.read(bound(p.spec.inventory_path,p.spec.inventory_sha256,mapping));if(JSON.stringify(request.inventory)!==JSON.stringify(inventory))throw Error('Inventory mismatch');const normalized=await c.normalized([...all],{complete:finalized});
 result={tools:p.tools,scopes:{project:{status:incomplete?'incomplete':'measured',components:components(normalized)},changed_files:{status:'unavailable',reason:'This frozen baseline declares no changed-file scope'},changed_lines:{status:'unavailable',reason:'This frozen baseline declares no changed-line scope'}}};
 }else throw Error('Unknown operation '+op);
 c.save(response,result);
})().catch(e=>{console.error(e.stack);process.exitCode=1});
