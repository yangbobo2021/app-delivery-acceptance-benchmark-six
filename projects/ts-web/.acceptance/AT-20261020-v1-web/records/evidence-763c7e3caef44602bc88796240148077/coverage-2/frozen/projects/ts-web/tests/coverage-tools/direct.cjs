// Independent reader: calls Istanbul directly; does not import the adapter/core.
const fs=require('node:fs');
const path=require('node:path');
const {createCoverageMap}=require('istanbul-lib-coverage');
const [route,raw]=process.argv.slice(2);
const root=path.resolve(__dirname,'../../../..');
const names=route==='browser'?['projects/ts-web/src/app.ts']:route==='build'?['projects/ts-web/build.mjs']:['projects/ts-web/server.mjs'];
const files=fs.readdirSync(raw).filter(n=>n.endsWith('.coverage.json')).sort();
if(!files.length)throw Error('No native snapshots');
const map=createCoverageMap({});
for(const name of files){const data=JSON.parse(fs.readFileSync(path.join(raw,name),'utf8'));if(!Object.keys(data).length)throw Error('Empty snapshot');map.merge(data);}
const components=names.map(name=>{
 const summary=map.fileCoverageFor(path.join(root,name)).toSummary().toJSON();
 const metric=key=>({status:'measured',covered:summary[key].covered,total:summary[key].total,pct:summary[key].pct});
 return {id:name,source_paths:[name],metrics:{line:metric('lines'),branch:metric('branches')}};
});
console.log(JSON.stringify({schema:'coverage-probe-normalized-v1',components}));
