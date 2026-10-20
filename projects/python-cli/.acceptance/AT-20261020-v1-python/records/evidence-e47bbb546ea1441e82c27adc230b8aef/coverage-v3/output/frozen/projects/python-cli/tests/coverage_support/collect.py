"""Isolated non-business probes and real-command supervisor."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
import coverage
from adapter import ROOT, config, read, selfcheck, sha, write

mode, raw = sys.argv[1], Path(sys.argv[2]).resolve()
rcfile = raw/'coverage.ini'
config(rcfile, raw, ROOT)
if mode == 'zero':
    selfcheck(raw/'failure-paths.json')
route = sys.argv[3] if mode != 'command' else 'subprocess'
write(raw/'lifecycle.json', {'started': False, 'complete': False, 'route': route, 'native': []})
cov = coverage.Coverage(config_file=str(rcfile))
code = 0
cov.start()
write(raw/'lifecycle.json', {'started': True, 'complete': False, 'route': route, 'native': []})
try:
    if mode == 'command':
        request = read(sys.argv[3])
        code = subprocess.run(request['command'], cwd=request['cwd'], env={**os.environ, **request.get('env', {})}).returncode
    elif route == 'subprocess':
        stmt = 'import invoice.__main__' if mode == 'nonzero' else 'pass'
        code = subprocess.run([sys.executable, '-B', '-E', '-c', stmt], cwd=ROOT/'projects/python-cli').returncode
    elif route == 'inprocess':
        if mode == 'nonzero':
            sys.path.insert(0, str(ROOT/'projects/python-cli'))
            importlib.import_module('invoice.__main__')
    else:
        raise ValueError('Unknown route')
finally:
    cov.stop()
    cov.save()
# Only reached after a normal collector finalization. Abrupt termination leaves
# an incomplete marker; a parent-only zero snapshot cannot validate a child.
files = sorted(raw.glob('.coverage.*'))
write(raw/'lifecycle.json', {'started': True, 'complete': True, 'route': route, 'exit_code': code,
    'native': [{'path': str(p), 'sha256': sha(p)} for p in files if p.is_file()]})
sys.exit(code)
