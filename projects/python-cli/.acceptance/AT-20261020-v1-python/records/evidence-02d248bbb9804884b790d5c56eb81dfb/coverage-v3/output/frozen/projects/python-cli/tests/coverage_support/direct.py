"""Independent reader: official coverage CLI, no adapter imports."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[4]
raw = Path(sys.argv[1]).resolve()
sources = ['projects/python-cli/invoice/__main__.py', 'projects/python-cli/invoice/totals.py']
marker = json.loads((raw/'lifecycle.json').read_text())
assert marker['started'] and marker['complete'], 'Collection did not finish'
assert marker['native'], 'No actual native snapshot'
if marker['route'] == 'subprocess':
    assert len(marker['native']) >= 2, 'Child snapshot missing'
with tempfile.TemporaryDirectory(prefix='coverage-independent-', dir=raw.parent) as tmp:
    folder = Path(tmp)
    for i, item in enumerate(marker['native']):
        file = Path(item['path'])
        assert hashlib.sha256(file.read_bytes()).hexdigest() == item['sha256']
        shutil.copyfile(file, folder/('.coverage.' + str(i)))
    base = str(folder/'.coverage')
    for argv in [
        [sys.executable, '-m', 'coverage', 'combine', '--data-file', base, str(folder)],
        [sys.executable, '-m', 'coverage', 'json', '--data-file', base, '-o', str(folder/'report.json'), *[str(root/s) for s in sources]]]:
        done = subprocess.run(argv, capture_output=True, text=True, cwd=root)
        if done.returncode:
            raise RuntimeError(done.stderr + done.stdout)
    report = json.loads((folder/'report.json').read_text())
    components = []
    for source in sources:
        native = next(v['summary'] for k, v in report['files'].items() if Path(k).resolve() == (root/source).resolve())
        components.append({'id': source, 'source_paths': [source], 'metrics': {
            'line': {'status': 'measured', 'covered': native['covered_lines'], 'total': native['num_statements'], 'pct': native['percent_statements_covered']},
            'branch': {'status': 'measured', 'covered': native['covered_branches'], 'total': native['num_branches'], 'pct': native['percent_branches_covered']}}})
print(json.dumps({'schema': 'coverage-probe-normalized-v1', 'components': components}, sort_keys=True))
