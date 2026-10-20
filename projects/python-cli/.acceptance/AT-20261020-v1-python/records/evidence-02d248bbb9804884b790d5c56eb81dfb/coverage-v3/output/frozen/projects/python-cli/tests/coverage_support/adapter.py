"""Project-owned coverage.py lifecycle; no product assertions or synthetic counts."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import coverage

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ['projects/python-cli/invoice/__main__.py', 'projects/python-cli/invoice/totals.py']
VERSION = '7.16.2'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def write(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')

def bound(p, digest=None, mapping=None):
    p = str(p)
    if Path(p).is_file() and (digest is None or sha(p) == digest):
        return Path(p)
    item = (mapping or {}).get(p + '#' + str(digest)) or (mapping or {}).get(p)
    if item and (digest is None or item['sha256'] == digest) and sha(item['path']) == item['sha256']:
        return Path(item['path'])
    raise ValueError('Missing or changed bound file: ' + p)

def toolcheck():
    assert coverage.__version__ == VERSION, 'coverage.py version changed'
    lock = read(Path(__file__).with_name('tool-lock.json'))
    dist = importlib.metadata.distribution('coverage')
    for name, digest in lock['files'].items():
        assert sha(dist.locate_file(name)) == digest, 'coverage.py installation changed: ' + name

def config(path, raw, root):
    # Trace the collector harness too. coverage.py 7.16.2 combine/update drops
    # branch mode when ALL input arc tables are empty. Real harness execution
    # preserves that mode; explicit product morfs exclude every harness hit.
    path.write_text('[run]\nbranch = True\nparallel = True\npatch = subprocess\nsigterm = True\nsource =\n    ' + str(root/'projects/python-cli/invoice') + '\n    ' + str(root/'projects/python-cli/tests/coverage_support') + '\ndata_file = ' + str(raw/'.coverage') + '\n')

def native_state(raw, mapping=None):
    marker = read(bound(Path(raw)/'lifecycle.json', mapping=mapping))
    files = []
    for item in marker.get('native', []):
        files.append(bound(item['path'], item['sha256'], mapping))
    reason = None
    if not marker.get('started'):
        reason = 'collection route did not start'
    elif not marker.get('complete'):
        reason = 'collection finalization did not complete'
    elif not files:
        reason = 'native snapshot missing; zero baseline is not an execution'
    elif marker.get('route') == 'subprocess' and len(files) < 2:
        reason = 'child native snapshot missing'
    return marker, files, reason

def collection_status(reason):
    return 'incomplete' if reason else 'measured'

def components(raw, root=ROOT, mapping=None, sources=None):
    sources = sources or {s: sha(root/s) for s in SOURCES}
    marker, files, reason = native_state(raw, mapping)
    if reason:
        return [{'id': s, 'label': s, 'source_paths': [s],
                 'line': {'status': 'unavailable', 'reason': reason},
                 'branch': {'status': 'unavailable', 'reason': reason}} for s in sources if s in SOURCES]
    paths = {str(root/s): str(bound(root/s, digest, mapping)) for s, digest in sources.items()}
    cov = coverage.Coverage(data_file=None, config_file=False, branch=True)
    merged = cov.get_data()
    for file in files:
        data = coverage.CoverageData(basename=str(file))
        data.read()
        if not data.has_arcs():
            raise ValueError('Native snapshot lacks branch collection metadata')
        merged.update(data, map_path=lambda p: paths.get(p, p))
    with tempfile.TemporaryDirectory(prefix='invoice-coverage-read-', dir=Path(raw).parent) as tmp:
        dest = Path(tmp)/'report.json'
        cov.json_report(morfs=[paths[str(root/s)] for s in sources if s in SOURCES], outfile=str(dest))
        report = read(dest)
    result = []
    for s in sources:
        if s not in SOURCES:
            continue
        target = Path(paths[str(root/s)]).resolve()
        summary = next(v['summary'] for k, v in report['files'].items() if Path(k).resolve() == target)
        result.append({'id': s, 'label': s, 'source_paths': [s],
                       'line': {'status': 'measured', 'covered': summary['covered_lines'], 'total': summary['num_statements'], 'pct': summary['percent_statements_covered']},
                       'branch': {'status': 'measured', 'covered': summary['covered_branches'], 'total': summary['num_branches'], 'pct': summary['percent_branches_covered']}})
    return result

def normalized(raw):
    return {'schema': 'coverage-probe-normalized-v1', 'components': [
        {'id': c['id'], 'source_paths': c['source_paths'], 'metrics': {'line': c['line'], 'branch': c['branch']}}
        for c in components(raw)]}

def profile(path, mapping=None):
    path = Path(path)
    if path.name != 'prepared.json':
        path = path/'prepared.json'
    p = read(bound(path, mapping=mapping))
    assert p['schema'] == 'project-coverage-preparation-v1'
    spec = p['spec']; root = Path(spec['project_root'])
    for name, digest in {**spec['source_hashes'], **p['adapter_files']}.items():
        bound(root/name, digest, mapping)
    for key, digest_key in [('runtime_manifest', 'runtime_sha256'), ('probe_report', 'probe_report_sha256'), ('inventory_path', 'inventory_sha256')]:
        bound(spec[key], spec[digest_key], mapping)
    runtime = read(bound(spec['runtime_manifest'], spec['runtime_sha256'], mapping))
    assert runtime['revision'] == spec['revision'] and runtime['workspace'] == str(root)
    probes = read(bound(spec['probe_report'], spec['probe_report_sha256'], mapping))
    assert probes['revision'] == spec['revision'] and probes['runtime_sha256'] == spec['runtime_sha256']
    assert probes['status'] in ('ready', 'partial')
    for route in probes['routes']:
        assert all(route['probes'][mode]['status'] == 'passed' for mode in ('zero', 'nonzero')), 'Collection route probe failed'
    measured = {s for route in probes['routes'] for s in route['source_paths']}
    assert set(SOURCES) <= measured, 'Missing product source probes'
    if not mapping:
        for exe in runtime['executables']:
            assert sha(Path(exe['path']).resolve()) == exe['sha256']
        for name, digest in runtime.get('dependency_hashes', {}).items():
            bound(root/name, digest)
    toolcheck()
    return p

def execute(req, req_path):
    p = profile(req['prepared']); root = Path(p['spec']['project_root'])
    prepared_path = Path(req['prepared'])
    if prepared_path.name != 'prepared.json':
        prepared_path = prepared_path/'prepared.json'
    assert sha(prepared_path) == req['prepared_sha256']
    assert Path(req['cwd']).resolve().is_relative_to(root)
    raw = Path(req['output'])/'native'; raw.mkdir(exist_ok=False)
    rcfile = raw/'coverage.ini'; config(rcfile, raw, root)
    write(raw/'lifecycle.json', {'started': False, 'complete': False, 'native': []})
    env = {**os.environ, **req.get('env', {})}
    # Start coverage in a dedicated supervisor: coverage.py patches child Python
    # startup, including children invoked with -E. No business argv is rewritten.
    cmd = [sys.executable, '-B', str(Path(__file__).with_name('collect.py')), 'command', str(raw), str(req_path)]
    done = subprocess.run(cmd, cwd=root, env=env)
    return {'exit_code': done.returncode, 'raw': str(raw)}, done.returncode

def finish(req, mapping=None):
    session = read(bound(req['request'], mapping=mapping)); p = profile(session['prepared'], mapping)
    raw = Path(session['output'])/'native'
    life = bound(raw/'lifecycle.json', mapping=mapping)
    marker, files, reason = native_state(raw, mapping)
    comps = components(raw, Path(p['spec']['project_root']), mapping, p['spec']['source_hashes'])
    return {'schema': 'project-tool-coverage-report-v1', 'protocol': 'project-coverage-v1',
            'prepared': session['prepared'], 'prepared_sha256': session['prepared_sha256'],
            'scene_id': session['scene_id'], 'revision': p['spec']['revision'], 'source_hashes': p['spec']['source_hashes'],
            'tools': p['tools'], 'collection_relation': 'same_run', 'status': collection_status(reason),
            'receipt_path': req['receipt'], 'execution_sha256': sha(bound(req['receipt'], mapping=mapping)),
            'raw_evidence': [*marker.get('native', []), {'path': str(raw/'lifecycle.json'), 'sha256': sha(life)}],
            'collection_lifecycle': {'path': str(raw/'lifecycle.json'), 'sha256': sha(life)},
            'execution_request': {'path': req['request'], 'sha256': sha(bound(req['request'], mapping=mapping))},
            'components': comps}

def checked_report(path, mapping=None):
    r = read(bound(path, mapping=mapping)); p = profile(r['prepared'], mapping)
    assert r['prepared_sha256'] == sha(bound(Path(r['prepared'])/'prepared.json', mapping=mapping))
    assert r['revision'] == p['spec']['revision'] and r['source_hashes'] == p['spec']['source_hashes']
    assert r['tools'] == p['tools']
    for item in [*r['raw_evidence'], r['execution_request'], r['collection_lifecycle']]:
        bound(item['path'], item['sha256'], mapping)
    receipt = read(bound(r['receipt_path'], r['execution_sha256'], mapping))
    session = read(bound(receipt['coverage_session_path'], receipt['coverage_session_sha256'], mapping))
    assert sha(bound(receipt['coverage_session_path'], mapping=mapping)) == r['execution_request']['sha256']
    assert session['scene_id'] == r['scene_id'] and session['prepared_sha256'] == r['prepared_sha256']
    actual = components(Path(session['output'])/'native', Path(p['spec']['project_root']), mapping, r['source_hashes'])
    assert actual == r['components'], 'native coverage differs from report'
    _, _, reason = native_state(Path(session['output'])/'native', mapping)
    assert r['status'] == collection_status(reason)
    return r, p

def summarize(req, mapping=None):
    checked = [checked_report(path, mapping) for path in req['reports']]
    assert checked and len({r['prepared_sha256'] for r, p in checked}) == 1
    p = checked[0][1]; spec = p['spec']
    inv = read(bound(spec['inventory_path'], spec['inventory_sha256'], mapping))
    assert req['inventory'] == inv
    with tempfile.TemporaryDirectory(prefix='invoice-coverage-merge-') as tmp:
        raw = Path(tmp); data = coverage.CoverageData(basename=str(raw/'.coverage'))
        incomplete = False
        for r, _ in checked:
            life = read(bound(r['collection_lifecycle']['path'], r['collection_lifecycle']['sha256'], mapping))
            incomplete |= r['status'] != 'measured'
            for item in life['native']:
                d = coverage.CoverageData(basename=str(bound(item['path'], item['sha256'], mapping))); d.read(); data.update(d)
        if data.has_arcs():
            data.write()
            write(raw/'lifecycle.json', {'started': True, 'complete': True, 'route': 'merged', 'native': [{'path': str(raw/'.coverage'), 'sha256': sha(raw/'.coverage')}]})
            comps = components(raw, Path(spec['project_root']), mapping, spec['source_hashes'])
            project = {'status': 'incomplete' if incomplete else 'measured', 'components': comps}
        else:
            project = {'status': 'unavailable', 'reason': 'No actual native snapshots'}
    reason = inv.get('changed_scope_reason', 'No frozen change scope available')
    # This baseline explicitly has no diff. Never reuse project counts for it.
    scopes = {'project': project}
    for scope in ['changed_files', 'changed_lines']:
        scopes[scope] = {'status': 'unavailable', 'reason': reason}
    return {'tools': p['tools'], 'scopes': scopes}

def selfcheck(output):
    toolcheck()
    with tempfile.TemporaryDirectory(prefix='coverage-failure-check-') as tmp:
        raw = Path(tmp); evidence = []
        for state in [
            {'started': False, 'complete': False, 'native': []},
            {'started': True, 'complete': True, 'native': []},
            {'started': True, 'complete': False, 'native': []}]:
            write(raw/'lifecycle.json', state)
            c = components(raw)
            _, _, reason = native_state(raw)
            status = collection_status(reason)
            assert status == 'incomplete'
            assert all(x[m]['status'] == 'unavailable' and 'covered' not in x[m]
                       for x in c for m in ('line', 'branch'))
            evidence.append({'input': state, 'status': status, 'reason': reason, 'output': c})
        write(output, {'tool_version': coverage.__version__, 'failure_paths': evidence, 'business_executed': False})
    return {'status': 'valid', 'evidence': str(output)}

if __name__ == '__main__':
    try:
        op = sys.argv[1]
        if op == 'probe-read':
            print(json.dumps(normalized(sys.argv[2]), sort_keys=True)); sys.exit(0)
        if op == 'selfcheck':
            print(json.dumps(selfcheck(sys.argv[2]))); sys.exit(0)
        req = read(sys.argv[2]); mapping = req.get('artifact_map', {}); code = 0
        if op == 'verify-preparation':
            profile(req['prepared'], mapping); result = {'status': 'valid'}
        elif op == 'run':
            result, code = execute(req, sys.argv[2])
        elif op == 'finish':
            result = finish(req, mapping)
        elif op == 'verify-report':
            checked_report(req['report'], mapping); result = {'status': 'valid'}
        elif op == 'summarize':
            result = summarize(req, mapping)
        else:
            raise ValueError('Unknown operation: ' + op)
        write(sys.argv[3], result); sys.exit(code)
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr); sys.exit(2)
