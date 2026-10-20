const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {createInstrumenter}=require('istanbul-lib-instrument');
const {createCoverageMap}=require('istanbul-lib-coverage');
const {createSourceMapStore}=require('istanbul-lib-source-maps');
const esbuild=require('../../node_modules/esbuild');
const root=path.resolve(__dirname,'../../../..'),project=path.join(root,'projects/electron-desktop');
const sources=['main','preload','renderer','store'].map(x=>'projects/electron-desktop/src/'+x+'.ts');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const save=(p,o)=>{fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(o,null,2)+'\n')};
function tools(){return ['istanbul-lib-instrument','istanbul-lib-coverage','istanbul-lib-source-maps'].map(name=>({name,version:require(name+'/package.json').version,role:({'istanbul-lib-instrument':'JavaScript instrumentation and native zero units','istanbul-lib-coverage':'native merge and line/branch statistics','istanbul-lib-source-maps':'TypeScript source map remapping'})[name]})).concat([{name:'esbuild',version:esbuild.version,role:'TypeScript transform and isolated Electron bundle'}]);}
async function build(out,mode='actual'){
 const units=path.join(out,'units'),app=path.join(out,'app');fs.mkdirSync(units,{recursive:true});fs.mkdirSync(app,{recursive:true});let baseline={};
 for(const source of sources){const name=path.basename(source,'.ts');const generated=path.join(units,name+'.js');const transformed=await esbuild.transform(fs.readFileSync(path.join(root,source),'utf8'),{loader:'ts',format:'cjs',sourcemap:'external',sourcefile:path.join(root,source),sourcesContent:true,target:'es2022'});
 const instrumenter=createInstrumenter({coverageGlobalScope:'globalThis',coverageGlobalScopeFunc:false,compact:false});
 const code=instrumenter.instrumentSync(transformed.code,generated,JSON.parse(transformed.map));baseline[generated]=instrumenter.lastFileCoverage();fs.writeFileSync(generated,code);
 }
 save(path.join(out,'baseline.json'),baseline);
 for(const name of ['main','preload','renderer']){
 if(mode==='zero'){
 const keys=name==='main'?['main','store']:[name];const cov=Object.fromEntries(Object.entries(baseline).filter(([p])=>keys.includes(path.basename(p,'.js'))));
 fs.writeFileSync(path.join(app,name+'.js'),'globalThis.__coverage__='+JSON.stringify(cov)+';');
 }else await esbuild.build({entryPoints:[path.join(units,name+'.js')],outfile:path.join(app,name+'.js'),bundle:true,platform:name==='renderer'?'browser':'node',external:['electron'],format:name==='renderer'?'iife':'cjs',logLevel:'silent'});
 }
 const publisher=`\n;(()=>{const token=${JSON.stringify(crypto.randomUUID())}+'-'+Math.random();globalThis.__acceptanceFlush=()=>console.debug('__ACCEPTANCE_COV__'+JSON.stringify({token,coverage:globalThis.__coverage__}));setInterval(globalThis.__acceptanceFlush,100);addEventListener('pagehide',globalThis.__acceptanceFlush);globalThis.__acceptanceFlush();})();\n`;
 for(const name of ['preload','renderer'])fs.appendFileSync(path.join(app,name+'.js'),publisher);
 fs.copyFileSync(mode==='zero'?path.join(__dirname,'zero.html'):path.join(project,'src/index.html'),path.join(app,'index.html'));
 fs.copyFileSync(path.join(__dirname,'electron-wrapper.cjs'),path.join(app,'wrapper.cjs'));
 save(path.join(app,'package.json'),{name:'acceptance-instrumented-local-notes',main:'wrapper.cjs'});
 return app;
}
async function normalized(files,lifecycle){
 const map=createCoverageMap({});for(const file of files){const value=read(file);map.merge(value.coverage||value);}
 const mapped=await createSourceMapStore().transformCoverage(map);const components=sources.map(source=>{
 const name=mapped.files().find(file=>file.endsWith('/'+source));if(!name)return {id:source,source_paths:[source],metrics:{line:{status:'unavailable',reason:'No actual native snapshot for this source'},branch:{status:'unavailable',reason:'No actual native snapshot for this source'}}};
 const summary=mapped.fileCoverageFor(name).toSummary().toJSON();const metrics={};for(const [key,native]of [['line','lines'],['branch','branches']]){const s=summary[native];metrics[key]={status:lifecycle?.complete===false?'incomplete':'measured',covered:s.covered,total:s.total,pct:s.pct};if(lifecycle?.complete===false)metrics[key].reason='Collector finalization incomplete';}
 return {id:source,source_paths:[source],metrics};});return {schema:'coverage-probe-normalized-v1',components};
}
function nativeFiles(dir){return fs.readdirSync(dir).filter(x=>/^snapshot-.*\.json$/.test(x)).map(x=>path.join(dir,x));}
module.exports={fs,path,root,project,sources,read,hash,save,tools,build,normalized,nativeFiles,createCoverageMap,createSourceMapStore};
