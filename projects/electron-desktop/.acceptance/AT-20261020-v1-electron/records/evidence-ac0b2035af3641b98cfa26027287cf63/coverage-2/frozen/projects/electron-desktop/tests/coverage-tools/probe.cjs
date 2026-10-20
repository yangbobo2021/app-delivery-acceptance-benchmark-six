const c=require('./core.cjs');const {spawn}=require('node:child_process');
(async()=>{const [op,raw,dir,mode,route]=process.argv.slice(2);
 if(op==='collect'){
 const app=await c.build(c.path.join(dir,'build'),mode);const env={...process.env,ACCEPTANCE_COVERAGE_RAW:raw,ACCEPTANCE_COVERAGE_MODE:mode,ACCEPTANCE_COVERAGE_PROBE:'1'};delete env.ELECTRON_RUN_AS_NODE;
 const executable=require('../../node_modules/electron');const child=spawn(executable,[app,'--user-data-dir',c.path.join(dir,'user-data')],{env,detached:true,stdio:['ignore','pipe','pipe']});let log='';child.stdout.on('data',b=>log+=b);child.stderr.on('data',b=>log+=b);let timedout=false;const timer=setTimeout(()=>{timedout=true;try{process.kill(-child.pid,'SIGKILL');}catch{child.kill('SIGKILL');}},25000);
 const code=await new Promise((res,rej)=>{child.on('error',rej);child.on('close',res)});clearTimeout(timer);c.fs.writeFileSync(c.path.join(dir,'electron.log'),log);if(code!==0||timedout)throw Error('Probe Electron did not close normally');
 const files=c.nativeFiles(raw);if(files.length<5)throw Error('Missing native process/world snapshots');const life=c.read(c.path.join(raw,c.fs.readdirSync(raw).find(n=>n.startsWith('lifecycle-')&&n.endsWith('.json'))));if(!life.complete)throw Error('Finalization failed');
 const missing=await c.normalized([],{complete:false});const unfinished=await c.normalized(files,{complete:false});
 const withoutMain=files.filter(file=>!c.path.basename(file).startsWith('snapshot-main-'));
 const missingMain=await c.normalized(withoutMain,{complete:true});
 if(missingMain.components.some(x=>/\/(main|store)\.ts$/.test(x.id)&&Object.values(x.metrics).some(m=>m.status!=='unavailable')))throw Error('Missing main snapshot became measured');
 if(!missingMain.components.some(x=>/\/(preload|renderer)\.ts$/.test(x.id)&&x.metrics.line.status==='measured'))throw Error('Partial-source failure probe lacks retained native evidence');
 if(missing.components.some(x=>Object.values(x.metrics).some(m=>m.status==='measured'))||unfinished.components.some(x=>Object.values(x.metrics).some(m=>m.status==='measured')))throw Error('Failure propagation regression');
 c.save(c.path.join(dir,'failure-paths.json'),{not_started:{native_files:[],normalized:missing},missing_snapshot:{native_files:[],normalized:missing},missing_main_snapshot:{native_files:withoutMain,normalized:missingMain},unfinished:{lifecycle:{complete:false},native_files:files,normalized:unfinished},note:'Fault injection into the read/finalization boundary only; actual probe snapshots are preserved unchanged.'});
 }else if(op==='read'){
 const files=c.nativeFiles(raw);if(!files.length)throw Error('Empty native data');const lives=c.fs.readdirSync(raw).filter(n=>/^lifecycle.*\.json$/.test(n));const result=await c.normalized(files,{complete:lives.length>0&&lives.every(n=>c.read(c.path.join(raw,n)).complete)});result.components=result.components.filter(x=>route==='main'?/\/(main|store)\.ts$/.test(x.id):/\/(preload|renderer)\.ts$/.test(x.id));console.log(JSON.stringify(result));
 }else throw Error('Unknown probe operation');
})().catch(e=>{console.error(e.stack);process.exitCode=1});
