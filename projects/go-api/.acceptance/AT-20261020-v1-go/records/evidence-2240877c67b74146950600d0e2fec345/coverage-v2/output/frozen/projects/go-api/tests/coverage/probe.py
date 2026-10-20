"""Host-invoked non-business probes. Never runs stock/reservation scenarios."""
import sys
sys.dont_write_bytecode = True
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import adapter

mode,rawarg,probearg=sys.argv[1:]
raw=Path(rawarg).resolve(); probe=Path(probearg).resolve()
binary=adapter.build(probe/'build')
life=probe/'build/lifecycle'
env=adapter.launch_env(binary,raw,life)
env['ACCEPTANCE_COVERAGE_MODE']='zero' if mode=='zero' else 'hit'
argv=['/opt/homebrew/bin/python3',str(adapter.HERE/'launcher.py')]
result=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=30)
adapter.save(probe/'collection-receipt.json',{'command':argv,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
 'native':[adapter.ref(p) for p in sorted(raw.iterdir()) if p.is_file()],'lifecycle':[adapter.ref(p) for p in sorted(life.iterdir())]})
if result.returncode: raise SystemExit('native probe execution failed; see collection-receipt.json')
state=adapter.collection_state(raw,life)
if state['status']!='complete': raise SystemExit('native probe did not finalize: '+json.dumps(state))

if mode=='zero':
 failures=probe/'failure-paths'; failures.mkdir()
 evidence=[]
 # Route never starts: no snapshot is allowed to turn into measured zero.
 missing=failures/'not-started'; missing.mkdir(); (missing/'raw').mkdir(); (missing/'life').mkdir()
 evidence.append({'case':'route-not-started','state':adapter.collection_state(missing/'raw',missing/'life'),
  'components':adapter.components(missing/'raw',False,'route never started')})
 # Actual completed native route, then missing counter dependency on a separate
 # evidence copy. Original native data remains untouched for independent readers.
 missing=failures/'snapshot-missing'; missing.mkdir(); (missing/'raw').mkdir(); (missing/'life').mkdir()
 for p in life.iterdir(): shutil.copyfile(p,missing/'life'/p.name)
 for p in raw.glob('covmeta.*'): shutil.copyfile(p,missing/'raw'/p.name)
 evidence.append({'case':'native-counter-snapshot-missing','state':adapter.collection_state(missing/'raw',missing/'life'),
  'components':adapter.components(missing/'raw',False,'counter snapshot missing')})
 # A real hard termination has no completed testing teardown. No HTTP requests.
 killed=failures/'hard-kill'; killed.mkdir(); (killed/'raw').mkdir(); (killed/'life').mkdir()
 killenv=adapter.launch_env(binary,killed/'raw',killed/'life')
 command=['/opt/homebrew/bin/python3',str(adapter.HERE/'launcher.py'),'--port','0','--state-dir',str(killed/'state')]
 with (killed/'process.log').open('w') as log:
  process=subprocess.Popen(command,env=killenv,stdout=log,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+10
   while 'Listening at' not in (killed/'process.log').read_text():
    if process.poll() is not None: raise RuntimeError('hard-kill route exited before startup')
    if time.monotonic()>deadline: raise RuntimeError('hard-kill route startup timeout')
    time.sleep(.02)
   process.kill(); exitcode=process.wait(timeout=5)
  finally:
   if process.poll() is None: process.kill(); process.wait(timeout=5)
 evidence.append({'case':'hard-killed-before-finalization','command':command,'exit_code':exitcode,
  'log':adapter.ref(killed/'process.log'),'state':adapter.collection_state(killed/'raw',killed/'life'),
  'components':adapter.components(killed/'raw',False,'process killed before finalization'),
  'native':[adapter.ref(p) for p in sorted((killed/'raw').iterdir()) if p.is_file()]})
 # Existing real snapshot plus lost finalization marker must remain incomplete.
 unfinished=failures/'unfinished-with-snapshot'; unfinished.mkdir(); (unfinished/'raw').mkdir(); (unfinished/'life').mkdir()
 for p in raw.iterdir(): shutil.copyfile(p,unfinished/'raw'/p.name)
 for p in life.glob('started.*'): shutil.copyfile(p,unfinished/'life'/p.name)
 state=adapter.collection_state(unfinished/'raw',unfinished/'life')
 evidence.append({'case':'native-snapshot-without-finalization','state':state,
  'components':adapter.components(unfinished/'raw',False,state['reason'])})
 for item in evidence:
  if item['state']['status']!='incomplete': raise RuntimeError('failure path did not propagate incomplete')
  if any(c['statement']['status']=='measured' for c in item['components']): raise RuntimeError('failure path falsely measured')
 adapter.save(failures/'evidence.json',{'status':'passed','cases':evidence})
print(json.dumps({'status':'collected','mode':mode,'state':state}))
