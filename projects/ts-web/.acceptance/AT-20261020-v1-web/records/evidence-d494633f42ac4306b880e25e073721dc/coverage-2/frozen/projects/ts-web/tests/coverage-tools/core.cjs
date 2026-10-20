const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {createInstrumenter}=require('istanbul-lib-instrument');
const {createCoverageMap}=require('istanbul-lib-coverage');
const esbuild=require('../../node_modules/esbuild');
const ROOT=path.resolve(__dirname,'../../../..');
const SOURCES=['projects/ts-web/server.mjs','projects/ts-web/src/app.ts','projects/ts-web/build.mjs'];
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n');
function instrument(name,sourcePath=path.join(ROOT,name),sourceRoot=ROOT){
 const i=createInstrumenter({esModules:true,compact:false,parserPlugins:['typescript'],coverageGlobalScope:'globalThis',coverageGlobalScopeFunc:false});
 let code=i.instrumentSync(fs.readFileSync(sourcePath,'utf8'),path.join(sourceRoot,name));
 const baseline=i.lastFileCoverage();
 // Counters are inserted against original TypeScript before esbuild strips types.
 if(name.endsWith('.ts')) code=esbuild.transformSync(code,{loader:'ts',target:'es2022',format:'esm'}).code;
 return {code,baseline};
}
function registration(name){
 const {code}=instrument(name);
 const babel=require('@babel/core');
 const ast=babel.parseSync(code,{configFile:false,babelrc:false,sourceType:'module'});
 const fn=ast.program.body.find(n=>n.type==='FunctionDeclaration' && /^cov_/.test(n.id.name));
 if(!fn) throw Error('Instrumenter registration function missing');
 return babel.transformFromAstSync(babel.types.file(babel.types.program([fn,babel.types.expressionStatement(babel.types.callExpression(babel.types.identifier(fn.id.name),[]))])),null,{configFile:false,babelrc:false}).code;
}
function nativeMap(files,resolveFile=p=>p){
 const map=createCoverageMap({});
 for(const file of files){const data=read(resolveFile(file)); if(!Object.keys(data).length) throw Error('Empty native snapshot');map.merge(data);}
 return map;
}
function components(map,names=SOURCES,complete=true,sourceRoot=ROOT){
 return names.map(name=>{
  const absolute=path.join(sourceRoot,name);
  const present=map.files().includes(absolute);
  const summary=present?map.fileCoverageFor(absolute).toSummary().toJSON():null;
  const metric=key=> !present?{status:'unavailable',reason:'No actual native runtime snapshot for this source; zero baseline is not substituted'}:{status:complete?'measured':'incomplete',covered:summary[key].covered,total:summary[key].total,pct:summary[key].pct,...(!complete?{reason:'Collection teardown did not complete'}:{})};
  return {id:name,label:name,source_paths:[name],line:metric('lines'),branch:metric('branches')};
 });
}
function snapshots(dir){return fs.existsSync(dir)?fs.readdirSync(dir).filter(n=>n.endsWith('.coverage.json')).sort().map(n=>path.join(dir,n)):[];}
module.exports={ROOT,SOURCES,hash,read,write,instrument,registration,nativeMap,components,snapshots};
