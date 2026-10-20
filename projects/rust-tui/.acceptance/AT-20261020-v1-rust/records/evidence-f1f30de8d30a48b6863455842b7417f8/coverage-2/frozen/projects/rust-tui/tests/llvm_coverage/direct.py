#!/usr/bin/env python3
"""Independent llvm-profdata/llvm-cov reference reader. Never imports adapter."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

cfg = json.loads((Path(__file__).resolve().parent/'config.json').read_text())
raw = Path(sys.argv[1])
profiles = sorted(raw.glob('*.profraw'))
if not profiles or any(p.stat().st_size == 0 for p in profiles):
    raise ValueError('No nonempty native snapshot')
tools = {}
for name in ('llvm-profdata', 'llvm-cov'):
    path = Path(cfg['tool_root'])/name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == cfg['tool_sha256'][name]
    tools[name] = str(path)
with tempfile.TemporaryDirectory(prefix='llvm-independent-reader-') as folder:
    indexed = str(Path(folder)/'independent.profdata')
    subprocess.run([tools['llvm-profdata'], 'merge', '-sparse', *map(str, profiles), '-o', indexed], check=True, capture_output=True)
    exported = subprocess.run([tools['llvm-cov'], 'export', '--summary-only', str(raw/'probe-binary'),
                               '-instr-profile='+indexed], check=True, capture_output=True, text=True)
    data = json.loads(exported.stdout)
files = [f for d in data['data'] for f in d['files'] if f['filename'].replace('\\','/').endswith('/'+cfg['source'])]
assert len(files) == 1
summary = files[0]['summary']
assert summary['lines']['count'] > 0
metrics = {'line': {'status': 'measured', 'covered': summary['lines']['covered'], 'total': summary['lines']['count']}}
b = summary.get('branches', {})
metrics['branch'] = ({'status':'measured','covered':b['covered'],'total':b['count']} if b.get('count', 0) else
    {'status':'unavailable','reason':'Stable rustc instrument-coverage emits no branch mapping; LLVM reports zero branch units'})
print(json.dumps({'schema':'coverage-probe-normalized-v1','components':[
    {'id':'rust-tui','source_paths':[cfg['source']],'metrics':metrics}]}))
