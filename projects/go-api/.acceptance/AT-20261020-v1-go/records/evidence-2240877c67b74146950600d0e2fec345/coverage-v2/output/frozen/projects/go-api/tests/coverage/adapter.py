"""Go-native coverage adapter. No executable-unit recognition or coverage arithmetic.

References: https://go.dev/doc/build-cover and https://pkg.go.dev/cmd/covdata
Counts and percentages come exclusively from Go covdata's debugdump/percent.
Product source is copied byte-for-byte into a per-execution test build. The
_test.go bridge is excluded by the Go toolchain from the measured denominator.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GO = '/opt/homebrew/bin/go'
SOURCE = 'projects/go-api/main.go'
LINE = {'status':'unavailable','reason':'Go native coverage measures statements, not executable lines'}
BRANCH = {'status':'unavailable','reason':'Go native coverage does not measure branches'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def save(p,v):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def ref(p): return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def bound(p,h,mapping=None):
 p=str(p)
 item=(mapping or {}).get(p+'#'+h) or (mapping or {}).get(p)
 if Path(p).is_file() and sha(p)==h: return Path(p)
 if isinstance(item,str): item={'path':item,'sha256':h}
 if item and item['sha256']==h and sha(item['path'])==h: return Path(item['path'])
 raise ValueError('frozen bytes missing or changed: '+p)
def tool(args, env=None, cwd=None):
 p=subprocess.run([GO,*args],env=env,cwd=cwd,text=True,capture_output=True,timeout=150)
 if p.returncode or p.stderr.strip(): raise ValueError('Go tool failed: '+repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout

def native(raw):
 raw=Path(raw)
 if not list(raw.glob('covmeta.*')) or not list(raw.glob('covcounters.*')):
  raise ValueError('actual native metadata and counter snapshot required; no zero-baseline substitution')
 dump=tool(['tool','covdata','debugdump','-pkg=stock.local/app','-i='+str(raw)])
 files=set(re.findall(r'^Srcfile: (.+)$',dump,re.M))
 if len(files)!=1 or Path(next(iter(files))).name!='main.go': raise ValueError('native source mapping mismatch: '+repr(files))
 found=re.search(r'^totalStmts: (\d+) coveredStmts: (\d+)$',dump,re.M)
 if not found or int(found[1])<=0: raise ValueError('no nonempty tool-owned denominator')
 pctout=tool(['tool','covdata','percent','-pkg=stock.local/app','-i='+str(raw)])
 pct=re.search(r'coverage:\s+([\d.]+)% of statements',pctout)
 if not pct: raise ValueError('native percentage missing')
 return {'status':'measured','label':'Go statements','covered':int(found[2]),'total':int(found[1]),'pct':float(pct[1]),'tool_output':found.group(0)+'\n'+pctout}

def normalized(raw):
 x=native(raw)
 return {'schema':'coverage-probe-normalized-v1','components':[{'id':'go-api','source_paths':[SOURCE],'metrics':{
  'line':LINE,'branch':BRANCH,'statement':{k:x[k] for k in ('status','covered','total')}}}]}

def components(raw,complete=True,reason=''):
 try:
  x=native(raw)
  if not complete: x={**x,'status':'incomplete','reason':reason}
 except ValueError as exc:
  x={'status':'unavailable','reason':str(exc)}
 return [{'id':'go-api','label':'Go API','source_paths':[SOURCE],'line':LINE,'branch':BRANCH,'statement':x}]

def build(folder, runtime=None):
 folder=Path(folder); folder.mkdir(parents=True,exist_ok=False)
 for n in ('src','cache','modcache','tmp','lifecycle'): (folder/n).mkdir()
 module=ROOT/'projects/go-api'
 for name in ('main.go','go.mod'): shutil.copyfile(module/name,folder/'src'/name)
 shutil.copyfile(HERE/'harness_test.go.txt',folder/'src'/'harness_test.go')
 assert sha(folder/'src/main.go')==sha(module/'main.go')
 env={**os.environ,'GOCACHE':str(folder/'cache'),'GOMODCACHE':str(folder/'modcache'),'GOTMPDIR':str(folder/'tmp'),
      'GOTOOLCHAIN':'local','GOENV':'off','GOWORK':'off','GOFLAGS':'','GOPROXY':'off','GOSUMDB':'off','CGO_ENABLED':'0'}
 command=['test','-c','-trimpath','-mod=readonly','-cover','-covermode=atomic','-coverpkg=stock.local/app','-o',str(folder/'stock.test'),'.']
 result=tool(command,env,folder/'src')
 save(folder/'build.json',{'command':[GO,*command],'stdout':result,'source':ref(folder/'src/main.go'),'module':ref(folder/'src/go.mod'),'binary':ref(folder/'stock.test')})
 return folder/'stock.test'

def launch_env(binary,raw,life):
 return {**os.environ,'ACCEPTANCE_COVERAGE_TEST_BINARY':str(binary),'ACCEPTANCE_COVERAGE_RAW':str(raw),
  'ACCEPTANCE_COVERAGE_LIFECYCLE':str(life),'ACCEPTANCE_COVERAGE_MODE':'','GOCOVERDIR':str(raw)}

def collection_state(raw,life):
 started=sorted(Path(life).glob('started.*'))
 missing=[]
 if not started: missing.append('collection route was never started')
 for p in started:
  pid=p.name.split('.')[-1]
  if not (Path(life)/('finished.'+pid)).is_file(): missing.append('unfinished process '+pid)
  if not list(Path(raw).glob('covcounters.*.'+pid+'.*')): missing.append('native counter snapshot absent for '+pid)
 if not list(Path(raw).glob('covmeta.*')): missing.append('native metadata absent')
 return {'status':'complete' if not missing else 'incomplete','reason':'; '.join(missing),'processes':[p.name.split('.')[-1] for p in started]}

def profile(prepared,mapping=None):
 p=Path(prepared)
 if p.is_dir(): p=p/'prepared.json'
 v=read(p); s=v['spec']
 if v['schema']!='project-coverage-preparation-v1': raise ValueError('wrong profile schema')
 runtime=read(bound(s['runtime_manifest'],s['runtime_sha256'],mapping))
 probes=read(bound(s['probe_report'],s['probe_report_sha256'],mapping))
 if runtime['workspace']!=s['project_root'] or runtime['revision']!=s['revision']: raise ValueError('runtime binding mismatch')
 if probes['runtime_sha256']!=s['runtime_sha256'] or probes['revision']!=s['revision']: raise ValueError('probe binding mismatch')
 for name,h in {**s['source_hashes'],**v['adapter_files']}.items(): bound(Path(s['project_root'])/name,h,mapping)
 bound(s['inventory_path'],s['inventory_sha256'],mapping)
 for e in runtime['executables']:
  if not mapping: bound(e['resolved_path'],e['sha256'])
 for name,h in runtime.get('dependency_hashes',{}).items():
  if not mapping: bound(Path(s['project_root'])/name,h)
 if not mapping:
  version=tool(['version']).strip()
  if version!=next(e['version_output'] for e in runtime['executables'] if e['name']=='go'): raise ValueError('tool version changed')
  if any(t['version']!='go1.25.7' for t in v['tools']): raise ValueError('unexpected tool version')
 for route in probes['routes']:
  for mode in ('zero','nonzero'):
   probe=route['probes'][mode]
   if probe['status']!='passed': raise ValueError('coverage route probe failed')
   for r in [*probe['receipts'].values(),*probe['native']]: bound(r['path'],r['sha256'],mapping)
   for r in probe['receipts'].values():
    receipt=read(bound(r['path'],r['sha256'],mapping))
    if receipt['exit_code']!=0: raise ValueError('failed probe receipt')
    for key in ('stdout','stderr'): bound(receipt[key]['path'],receipt[key]['sha256'],mapping)
 bound(probes['plan'],probes['plan_sha256'],mapping)
 for item in v.get('preparation_evidence',[]): bound(item['path'],item['sha256'],mapping)
 return v

def run(req):
 v=profile(Path(req['prepared'])/'prepared.json'); out=Path(req['output'])
 if sha(Path(req['prepared'])/'prepared.json')!=req['prepared_sha256']: raise ValueError('prepared digest mismatch')
 if req['cwd']!=v['spec']['project_root']: raise ValueError('session workspace differs')
 binary=build(out/'go-build'); raw=out/'native'; raw.mkdir(exist_ok=False)
 life=out/'go-build/lifecycle'
 env={**launch_env(binary,raw,life),**req.get('env',{})}
 # The formal test must launch this instrumented entry for each API subprocess.
 # Replace exact frozen-runtime stock paths in argv/env as a compatibility route.
 runtime=read(v['spec']['runtime_manifest'])
 originals=[str(Path(runtime['runtime_root'])/'bin/stock')]
 def replace(value):
  for original in originals: value=value.replace(original,str(HERE/'launcher.py'))
  return value
 command=[replace(x) for x in req['command']]
 env={k:replace(val) for k,val in env.items()}
 env.update(launch_env(binary,raw,life))
 env.update({k:replace(val) for k,val in req.get('env',{}).items() if not k.startswith('ACCEPTANCE_COVERAGE_') and k!='GOCOVERDIR'})
 env['STOCK_BINARY']=str(HERE/'launcher.py'); env['ACCEPTANCE_APP_BINARY']=str(HERE/'launcher.py')
 code=98
 try:
  proc=subprocess.run(command,cwd=req['cwd'],env=env)
  code=proc.returncode
 finally:
  # Stop leftover API children and wait for their Go testing teardown markers.
  for started in life.glob('started.*'):
   pid=int(started.name.split('.')[-1])
   if not (life/('finished.'+str(pid))).exists():
    try: os.kill(pid,signal.SIGTERM)
    except ProcessLookupError: pass
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   if all((life/('finished.'+p.name.split('.')[-1])).exists() for p in life.glob('started.*')): break
   time.sleep(.05)
  state=collection_state(raw,life)
  if state['status']!='complete':
   for started in life.glob('started.*'):
    pid=int(started.name.split('.')[-1])
    if not (life/('finished.'+str(pid))).exists():
     try: os.kill(pid,signal.SIGKILL)
     except ProcessLookupError: pass
  save(out/'collection.json',{**state,'command':command,'business_exit_code':code,
   'native':[ref(p) for p in sorted(raw.iterdir()) if p.is_file()],
   'lifecycle':[ref(p) for p in sorted(life.iterdir()) if p.is_file()]})
 return {'status':state['status'],'exit_code':code,'collection':ref(out/'collection.json')},code

def report_data(req,mapping=None):
 session=read(req['request']); out=Path(session['output'])
 v=profile(Path(session['prepared'])/'prepared.json',mapping)
 receipt=read(req['receipt'])
 if receipt['coverage_session_sha256']!=sha(req['request']): raise ValueError('session receipt mismatch')
 state=read(out/'collection.json')
 actual=collection_state(out/'native',out/'go-build/lifecycle')
 if actual['status']!=state['status'] or actual['reason']!=state['reason']: raise ValueError('collection state changed')
 complete=state['status']=='complete'
 cc=components(out/'native',complete,state['reason'])
 measured=complete and cc[0]['statement']['status']=='measured'
 evidence=state['native'] or [{**ref(out/'collection.json'),'role':'collection_failure_no_native_snapshot'}]
 result={'schema':'project-tool-coverage-report-v1','protocol':'project-coverage-v1','prepared':session['prepared'],
  'prepared_sha256':session['prepared_sha256'],'scene_id':session['scene_id'],'revision':v['spec']['revision'],
  'source_hashes':v['spec']['source_hashes'],'tools':v['tools'],'collection_relation':'same_run',
  'status':'measured' if measured else 'incomplete','receipt_path':str(Path(req['receipt']).resolve()),
  'execution_sha256':sha(req['receipt']),'raw_evidence':evidence,'components':cc,
  'session':ref(req['request']),'collection':ref(out/'collection.json')}
 for i,item in enumerate(state['lifecycle']): result['lifecycle_'+str(i)]=item
 return result

def verified_report(path,mapping=None):
 r=read(path); v=profile(Path(r['prepared'])/'prepared.json',mapping)
 for item in [r['session'],r['collection'],{'path':r['receipt_path'],'sha256':r['execution_sha256']},*r['raw_evidence']]: bound(item['path'],item['sha256'],mapping)
 state=read(bound(r['collection']['path'],r['collection']['sha256'],mapping))
 session=read(bound(r['session']['path'],r['session']['sha256'],mapping))
 receipt=read(bound(r['receipt_path'],r['execution_sha256'],mapping))
 if receipt['coverage_session_sha256']!=r['session']['sha256'] or session['scene_id']!=r['scene_id']: raise ValueError('receipt/session identity mismatch')
 if session['prepared_sha256']!=r['prepared_sha256'] or session['prepared']!=r['prepared']: raise ValueError('report preparation binding mismatch')
 for item in state['lifecycle']: bound(item['path'],item['sha256'],mapping)
 with tempfile.TemporaryDirectory(prefix='go-coverage-read-') as temp:
  life=Path(temp)/'lifecycle'; life.mkdir()
  for item in state['lifecycle']: shutil.copyfile(bound(item['path'],item['sha256'],mapping),life/Path(item['path']).name)
  for item in state['native']:
   shutil.copyfile(bound(item['path'],item['sha256'],mapping),Path(temp)/Path(item['path']).name)
  actual_state=collection_state(temp,life)
  if any(state[k]!=actual_state[k] for k in ('status','reason','processes')): raise ValueError('lifecycle does not prove collection state')
  if state['native'] and r['raw_evidence']!=state['native']: raise ValueError('native evidence does not match collection')
  complete=state['status']=='complete'
  actual=components(temp,complete,state['reason'])
  if r['components']!=actual: raise ValueError('native tool recomputation differs from report')
  if r['status']!=('measured' if complete and actual[0]['statement']['status']=='measured' else 'incomplete'): raise ValueError('report completeness differs')
 return r,v,state

def summarize(req,mapping=None):
 checked=[verified_report(p,mapping) for p in req['reports']]
 if not checked or len({r['prepared_sha256'] for r,_,_ in checked})!=1: raise ValueError('incompatible reports')
 v=checked[0][1]; s=v['spec']; inventory=read(bound(s['inventory_path'],s['inventory_sha256'],mapping))
 if req['inventory']!=inventory: raise ValueError('scope inventory differs')
 with tempfile.TemporaryDirectory(prefix='go-coverage-merge-') as temp:
  dirs=[]
  for i,(_,_,state) in enumerate(checked):
   folder=Path(temp)/str(i); folder.mkdir()
   for item in state['native']: shutil.copyfile(bound(item['path'],item['sha256'],mapping),folder/Path(item['path']).name)
   if state['native']: dirs.append(str(folder))
  merged=Path(temp)/'merged'; merged.mkdir()
  if dirs: tool(['tool','covdata','merge','-i='+','.join(dirs),'-o='+str(merged)])
  complete=all(r['status']=='measured' for r,_,_ in checked)
  result={'status':'measured' if complete else 'incomplete','components':components(merged,complete,'one or more collection routes incomplete')}
  reason=inventory.get('changed_scope_reason','No frozen changed-file or changed-line scope was supplied')
  return {'tools':v['tools'],'scopes':{'project':result,'changed_files':{'status':'unavailable','reason':reason},'changed_lines':{'status':'unavailable','reason':reason}}}

def main():
 if sys.argv[1:] == ['--self-check']:
  print(json.dumps({'status':'started','version':tool(['version']).strip(),'tool':'go tool covdata','docs':['https://go.dev/doc/build-cover','https://pkg.go.dev/cmd/covdata']})); return 0
 if sys.argv[1]=='probe-read': print(json.dumps(normalized(sys.argv[2]))); return 0
 op,request,response=sys.argv[1:]; req=read(request); mapping=req.get('artifact_map',{})
 if op=='verify-preparation': profile(req['prepared'],mapping); value={'status':'valid'}; code=0
 elif op=='run': value,code=run(req)
 elif op=='finish': value=report_data(req,mapping); code=0
 elif op=='verify-report': verified_report(req['report'],mapping); value={'status':'valid'}; code=0
 elif op=='summarize': value=summarize(req,mapping); code=0
 else: raise ValueError('unknown operation '+op)
 save(response,value); return code

if __name__=='__main__':
 try: sys.exit(main())
 except Exception as exc:
  if len(sys.argv)==4:
   save(sys.argv[3],{'status':'invalid','reason':str(exc)})
  print(str(exc),file=sys.stderr); sys.exit(2)
