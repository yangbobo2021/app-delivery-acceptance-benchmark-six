"""Independent direct Go reader; deliberately does not import the adapter."""
import json
import pathlib
import re
import subprocess
import sys
raw = pathlib.Path(sys.argv[1])
if not list(raw.glob('covmeta.*')) or not list(raw.glob('covcounters.*')):
    raise SystemExit('native metadata AND actual counter snapshot required')
r = subprocess.run(['/opt/homebrew/bin/go', 'tool', 'covdata', 'debugdump', '-pkg=stock.local/app', '-i='+str(raw)], capture_output=True, text=True, check=True)
if r.stderr.strip(): raise SystemExit(r.stderr)
files = set(re.findall(r'^Srcfile: (.+)$', r.stdout, re.M))
if len(files) != 1 or pathlib.Path(next(iter(files))).name != 'main.go':
    raise SystemExit('unexpected tool source mapping: '+repr(files))
m = re.search(r'^totalStmts: (\d+) coveredStmts: (\d+)$', r.stdout, re.M)
if not m or int(m[1]) <= 0: raise SystemExit('missing nonzero native denominator')
print(json.dumps({'schema':'coverage-probe-normalized-v1','components':[{'id':'go-api','source_paths':['projects/go-api/main.go'],'metrics':{
 'line':{'status':'unavailable','reason':'Go native coverage measures statements, not executable lines'},
 'branch':{'status':'unavailable','reason':'Go native coverage does not measure branches'},
 'statement':{'status':'measured','covered':int(m[2]),'total':int(m[1])}}}]}))
