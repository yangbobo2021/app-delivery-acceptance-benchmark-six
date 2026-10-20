// Business tests import launch(); keep the returned process alive for their UI assertions,
// then ask the application to quit normally. Killing it makes coverage incomplete.
const {spawn}=require('node:child_process');const path=require('node:path');
module.exports.launch=function(args=[],options={}){
 const app=process.env.ACCEPTANCE_ELECTRON_APP;if(!app)throw Error('Run through the acceptance coverage entry');
 const electron=require('../../node_modules/electron');const env={...process.env,...options.env};delete env.ELECTRON_RUN_AS_NODE;
 return spawn(electron,[app,...args],{detached:true,...options,env,stdio:options.stdio||'inherit'});
};
