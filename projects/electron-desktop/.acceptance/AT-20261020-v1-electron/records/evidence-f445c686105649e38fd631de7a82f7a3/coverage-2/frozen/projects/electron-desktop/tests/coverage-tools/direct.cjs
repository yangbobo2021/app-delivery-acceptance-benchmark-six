// Independent reader: deliberately does not import core.cjs, probe.cjs or adapter.cjs.
const fs=require('node:fs'),path=require('node:path');const {createCoverageMap}=require('istanbul-lib-coverage');const {createSourceMapStore}=require('istanbul-lib-source-maps');
(async()=>{const [raw,route]=process.argv.slice(2);const files=fs.readdirSync(raw).filter(n=>/^snapshot-.*\.json$/.test(n));if(!files.length)throw Error('No native snapshots');const coverage=createCoverageMap({});for(const name of files){const data=JSON.parse(fs.readFileSync(path.join(raw,name)));coverage.merge(data.coverage||data);}
 const lives=fs.readdirSync(raw).filter(n=>/^lifecycle.*\.json$/.test(n));if(!lives.length||!lives.every(n=>JSON.parse(fs.readFileSync(path.join(raw,n))).complete))throw Error('Collector finalization missing or incomplete');
 const mapped=await createSourceMapStore().transformCoverage(coverage);const root=path.resolve(__dirname,'../../../..');const result=[];
 for(const name of (route==='main'?['main','store']:['preload','renderer'])){const source='projects/electron-desktop/src/'+name+'.ts';const stats=mapped.fileCoverageFor(path.join(root,source)).toSummary().toJSON();const metrics={};for(const [label,key]of [['line','lines'],['branch','branches']])metrics[label]={status:'measured',covered:stats[key].covered,total:stats[key].total,pct:stats[key].pct};result.push({id:source,source_paths:[source],metrics});}
 console.log(JSON.stringify({schema:'coverage-probe-normalized-v1',components:result}));
})().catch(e=>{console.error(e.stack);process.exitCode=1});
