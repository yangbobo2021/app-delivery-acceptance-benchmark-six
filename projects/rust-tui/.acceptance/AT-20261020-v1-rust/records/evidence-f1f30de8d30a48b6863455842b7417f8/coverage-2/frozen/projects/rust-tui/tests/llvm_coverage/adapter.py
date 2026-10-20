#!/usr/bin/env python3
"""Project-owned LLVM lifecycle/format adapter; LLVM owns all coverage counts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'config.json').read_text())
SOURCE = CONFIG['source']
MAPPING = {}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resolve(path, digest=None):
    path = str(path)
    p = Path(path)
    if p.is_file() and (digest is None or sha(p) == digest):
        return p
    item = MAPPING.get(path + '#' + digest) if digest else None
    item = item or MAPPING.get(path)
    if item:
        p = Path(item['path'] if isinstance(item, dict) else item)
    if digest and (not p.is_file() or sha(p) != digest):
        raise ValueError('bound artifact missing or changed: ' + path)
    return p

def read(path, digest=None):
    return json.loads(resolve(path, digest).read_text())

def write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def ref(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}

def call(argv, **kwargs):
    result = subprocess.run(list(map(str, argv)), capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(json.dumps({'command': list(map(str, argv)), 'exit_code': result.returncode,
                                      'stdout': result.stdout, 'stderr': result.stderr}))
    return result.stdout

def tool(name):
    p = Path(CONFIG['tool_root']) / name
    if sha(p) != CONFIG['tool_sha256'][name]:
        raise ValueError('LLVM tool changed: ' + name)
    return p

def runtime(profile=None):
    spec = profile['spec'] if profile else CONFIG
    r = read(spec['runtime_manifest'], spec['runtime_sha256'])
    assert r['schema'] == 'project-runtime-preparation-v1' and r['status'] == 'ready'
    for item in r['executables']:
        assert sha(item['resolved_path']) == item['sha256']
    for name, digest in r['dependency_hashes'].items():
        resolve(Path(r['workspace']) / name, digest)
    return r

def environment(r, target):
    env = os.environ.copy()
    env.update(r['setup'][-1]['env'])
    env.update(CARGO_TARGET_DIR=str(target), RUSTFLAGS='-C instrument-coverage -C link-dead-code',
               CARGO_ENCODED_RUSTFLAGS='', RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='')
    # Empty encoded flags would override RUSTFLAGS in Cargo.
    env.pop('CARGO_ENCODED_RUSTFLAGS', None)
    env['PATH'] = str(Path(env['RUSTC']).parent) + os.pathsep + env.get('PATH', '')
    env['LLVM_PROFILE_FILE'] = str(Path(target).parent/'build-only-profiles'/'build-%p-%m.profraw')
    return env

def build(r, target):
    env = environment(r, target)
    cargo = next(x['path'] for x in r['executables'] if x['name'] == 'cargo')
    log = call([cargo, 'build', '--locked', '--offline'], cwd=Path(r['workspace'])/'projects/rust-tui', env=env)
    return env, Path(target)/'debug/terminal-checklist', log

def unavailable(reason):
    return {'status': 'unavailable', 'reason': reason}

def component(line, branch):
    return {'id': 'rust-tui', 'label': 'Rust TUI (LLVM)', 'source_paths': [SOURCE], 'line': line, 'branch': branch}

def native_metrics(binary, profiles):
    if not profiles:
        return component(unavailable('No actual native profile snapshot from this execution'),
                         unavailable('No actual native profile snapshot from this execution'))
    with tempfile.TemporaryDirectory(prefix='rust-coverage-reader-') as d:
        indexed = Path(d)/'merged.profdata'
        call([tool('llvm-profdata'), 'merge', '-sparse', *profiles, '-o', indexed])
        data = json.loads(call([tool('llvm-cov'), 'export', '--summary-only', binary,
                               '-instr-profile=' + str(indexed)]))
    files = [f for unit in data['data'] for f in unit['files']
             if f['filename'].replace('\\', '/').endswith('/' + SOURCE)]
    if len(files) != 1 or files[0]['summary']['lines']['count'] <= 0:
        raise ValueError('LLVM did not expose exactly one nonempty source denominator')
    summary = files[0]['summary']
    lines = summary['lines']
    line = {'status': 'measured', 'covered': lines['covered'], 'total': lines['count'], 'pct': lines['percent']}
    b = summary.get('branches', {})
    branch = ({'status': 'measured', 'covered': b['covered'], 'total': b['count'], 'pct': b['percent']}
              if b.get('count', 0) else unavailable('Stable rustc instrument-coverage emits no branch mapping; LLVM reports zero branch units'))
    return component(line, branch)

def normalized(binary, profiles):
    c = native_metrics(binary, profiles)
    return {'schema': 'coverage-probe-normalized-v1', 'components': [
        {'id': c['id'], 'source_paths': c['source_paths'], 'metrics': {
            key: {k: v for k, v in c[key].items() if k != 'pct'} for key in ('line', 'branch')}}]}

def collection_state(started, complete, profiles):
    if not started:
        return unavailable('collection route never started')
    if not complete:
        return unavailable('collection finalization did not complete')
    if not profiles:
        return unavailable('no actual native snapshot')
    return {'status': 'measured'}

def probe_collect(raw, mode):
    raw = Path(raw)
    folder = raw.parent
    r = runtime()
    env, binary, log = build(r, folder/'build')
    (folder/'build.log').write_text(log)
    rustc = next(x['path'] for x in r['executables'] if x['name'] == 'rustc')
    env['COVERAGE_WORKSPACE'] = r['workspace']
    deps = folder/'build/debug/deps'
    libs = list(deps.glob('libcrossterm-*.rlib'))
    assert len(libs) == 1
    argv = [rustc, HERE/'probe.rs', '--edition=2021', '--crate-name', 'coverage_probe',
            '-C', 'instrument-coverage', '-C', 'link-dead-code', '-L', 'dependency='+str(deps),
            '--extern', 'crossterm='+str(libs[0]), '-o', raw/'probe-binary']
    (folder/'rustc.log').write_text(call(argv, env=env))
    env['LLVM_PROFILE_FILE'] = str(raw/'probe-%p-%m.profraw')
    result = subprocess.run([str(raw/'probe-binary')] + (['touch'] if mode == 'nonzero' else []), env=env,
                            capture_output=True, text=True)
    write(folder/'probe-execution.json', {'argv': [str(raw/'probe-binary'), mode],
          'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    assert result.returncode == 0
    # State-propagation checks use absent paths and an unfinished lifecycle,
    # never a fabricated native snapshot or a substituted zero baseline.
    failures = {}
    for name, args in {'route-not-started': (False, False, []),
                       'native-missing': (True, True, []),
                       'finish-interrupted': (True, False, list(raw.glob('*.profraw')))}.items():
        state = collection_state(*args)
        components, status = report_components({'started': args[0], 'complete': args[1]}, raw/'probe-binary', args[2])
        assert state['status'] == 'unavailable' and 'covered' not in state
        assert status == 'incomplete' and all(c['line']['status'] == 'unavailable' and 'covered' not in c['line'] for c in components)
        failures[name] = {'collection_state': state, 'report_status': status, 'components': components}
    try:
        native_metrics(raw/'probe-binary', [folder/'definitely-missing.profraw'])
        raise AssertionError('LLVM accepted missing profile')
    except RuntimeError as e:
        failures['llvm-missing-profile-rejection'] = {'status': 'rejected', 'evidence': str(e)}
    write(folder/'failure-paths.json', failures)
    print(json.dumps({'failure_paths': failures, 'evidence': ref(folder/'failure-paths.json')}))

def load_profile(prepared, digest=None):
    p = Path(prepared)
    if p.suffix != '.json': p = p/'prepared.json'
    return read(p, digest)

def verify_preparation(req):
    p = load_profile(req['prepared'])
    r = runtime(p)
    spec = p['spec']
    assert r['workspace'] == spec['project_root'] and r['revision'] == spec['revision']
    probes = read(spec['probe_report'], spec['probe_report_sha256'])
    assert probes['runtime_sha256'] == spec['runtime_sha256'] and probes['status'] == 'ready'
    for route in probes['routes']:
        for mode in ('zero', 'nonzero'):
            assert route['probes'][mode]['status'] == 'passed'
            for item in route['probes'][mode]['native']:
                resolve(item['path'], item['sha256'])
    for name, digest in {**p['adapter_files'], **spec['source_hashes']}.items():
        resolve(Path(spec['project_root'])/name, digest)
    for name in ('llvm-cov', 'llvm-profdata'):
        version = call([tool(name), '--version']).strip()
        assert any(t['name'] == name and t['version'] == version for t in p['tools'])
    return {'status': 'valid'}

def run(req, response):
    profile = load_profile(req['prepared'], req['prepared_sha256'])
    r = runtime(profile)
    out = Path(req['output'])
    raw = out/'native'
    raw.mkdir(parents=True, exist_ok=False)
    life = {'started': False, 'complete': False, 'exit_code': None, 'command': req['command']}
    write(out/'collection.json', life)
    try:
        env, binary, log = build(r, out/'instrumented-target')
        (out/'coverage-build.log').write_text(log)
        shutil.copy2(binary, raw/'product-binary')
        # Business-supplied environment may contain the runtime's old target.
        # Preserve instrumented build settings after applying other variables.
        instrument = {k: env[k] for k in ('CARGO_HOME','CARGO_TARGET_DIR','RUSTC','RUSTFLAGS','PATH')}
        env.update(req.get('env', {})); env.update(instrument)
        env.pop('CARGO_ENCODED_RUSTFLAGS', None)
        env['LLVM_PROFILE_FILE'] = str(raw/'run-%p-%m.profraw')
        env['COVERAGE_PRODUCT_BINARY'] = str(binary)
        life['started'] = True
        life['binary'] = ref(raw/'product-binary')
        life['session_sha256'] = sha(sys.argv[2])
        write(out/'collection.json', life)
        child = subprocess.run(req['command'], cwd=req['cwd'], env=env)
        life.update(complete=True, exit_code=child.returncode)
        write(out/'collection.json', life)
        write(response, {'status': 'finished', 'exit_code': child.returncode, 'collection': ref(out/'collection.json')})
        return child.returncode
    except BaseException as error:
        life['error'] = str(error)
        write(out/'collection.json', life)
        write(response, {'status': 'incomplete', 'collection': ref(out/'collection.json')})
        raise

def report_components(life, binary, profiles):
    state = collection_state(life.get('started'), life.get('complete'), profiles)
    if state['status'] != 'measured':
        return [component(state, unavailable(state['reason']))], 'incomplete'
    return [native_metrics(binary, profiles)], 'measured'

def finish(req):
    session = read(req['request']); receipt = read(req['receipt'])
    profile = load_profile(session['prepared'], session['prepared_sha256'])
    out = Path(req['output']); raw = out/'native'
    life = read(out/'collection.json')
    assert life['command'] == session['command']
    assert receipt['coverage_session_sha256'] == sha(req['request'])
    if life.get('started'): assert life['session_sha256'] == sha(req['request'])
    if life.get('exit_code') != receipt['exit_code']:
        life = {**life, 'complete': False}
    binary = raw/'product-binary'; profiles = sorted(raw.glob('*.profraw'))
    components, status = report_components(life, binary, profiles)
    evidence = [ref(x) for x in [binary, *profiles] if x.is_file()]
    if not evidence:
        raise ValueError('No native evidence; cannot publish a coverage report')
    if status == 'measured':
        archive = raw/'llvm-native-archive'
        archive.mkdir(exist_ok=False)
        profdata = tool('llvm-profdata')
        cov = tool('llvm-cov')
        merged = archive/'merged.profdata'
        merge_argv = [profdata, 'merge', '-sparse', *profiles, '-o', merged]
        call(merge_argv)
        export_argv = [cov, 'export', binary, '-instr-profile=' + str(merged)]
        summary_argv = [cov, 'export', '--summary-only', binary, '-instr-profile=' + str(merged)]
        (archive/'native-export.stdout').write_text(call(export_argv))
        (archive/'native-summary.stdout').write_text(call(summary_argv))
        processing = {
            'schema': 'llvm-native-archive-v1',
            'binary': ref(binary), 'profiles': [ref(p) for p in profiles],
            'merged': ref(merged),
            'commands': [list(map(str, argv)) for argv in (merge_argv, export_argv, summary_argv)],
            'export': ref(archive/'native-export.stdout'),
            'summary': ref(archive/'native-summary.stdout'),
            'tools': [{'name': name, 'version': call([tool(name), '--version']).strip()}
                      for name in ('llvm-profdata', 'llvm-cov')],
        }
        write(archive/'processing.json', processing)
        evidence.extend(ref(p) for p in sorted(archive.iterdir()) if p.is_file())
    return {'schema': 'project-tool-coverage-report-v1', 'protocol': 'project-coverage-v1',
        'prepared': session['prepared'], 'prepared_sha256': session['prepared_sha256'],
        'scene_id': session['scene_id'], 'revision': profile['spec']['revision'],
        'source_hashes': profile['spec']['source_hashes'], 'tools': profile['tools'],
        'collection_relation': 'same_run', 'status': status, 'receipt_path': req['receipt'],
        'execution_sha256': sha(req['receipt']), 'raw_evidence': evidence, 'components': components,
        'collection': ref(out/'collection.json'), 'execution_request': ref(req['request'])}

def verify_report(path):
    report = read(path)
    profile = load_profile(report['prepared'], report['prepared_sha256'])
    life = read(report['collection']['path'], report['collection']['sha256'])
    session = read(report['execution_request']['path'], report['execution_request']['sha256'])
    receipt = read(report['receipt_path'], report['execution_sha256'])
    assert session['command'] == life['command']
    assert session['scene_id'] == report['scene_id']
    assert receipt['coverage_session_sha256'] == report['execution_request']['sha256']
    if life.get('started'): assert life['session_sha256'] == report['execution_request']['sha256']
    if life.get('exit_code') != receipt['exit_code']: life = {**life, 'complete': False}
    evidence = [(x, resolve(x['path'], x['sha256'])) for x in report['raw_evidence']]
    bins = [p for x,p in evidence if Path(x['path']).name == 'product-binary']
    profiles = [p for x,p in evidence if x['path'].endswith('.profraw')]
    components, status = report_components(life, bins[0] if bins else None, profiles)
    assert components == report['components'] and status == report['status']
    if status == 'measured':
        archived = {Path(item['path']).name: p for item, p in evidence
                    if 'llvm-native-archive' in Path(item['path']).parts}
        assert {'merged.profdata', 'native-export.stdout', 'native-summary.stdout',
                'processing.json'} <= archived.keys()
        processing = json.loads(archived['processing.json'].read_text())
        assert processing['binary']['sha256'] == sha(bins[0])
        assert sorted(x['sha256'] for x in processing['profiles']) == sorted(sha(p) for p in profiles)
        assert processing['merged']['sha256'] == sha(archived['merged.profdata'])
        assert processing['export']['sha256'] == sha(archived['native-export.stdout'])
        assert processing['summary']['sha256'] == sha(archived['native-summary.stdout'])
    assert report['source_hashes'] == profile['spec']['source_hashes']
    return report, profile, bins, profiles

def summarize(req):
    items = [verify_report(x) for x in req['reports']]
    assert items and len({r['prepared_sha256'] for r,p,b,s in items}) == 1
    profile = items[0][1]
    inventory = read(profile['spec']['inventory_path'], profile['spec']['inventory_sha256'])
    assert inventory == req['inventory']
    profiles = [s for r,p,b,ss in items for s in ss]
    if all(r['status'] == 'measured' for r,p,b,s in items):
        # All instrumented builds have the same frozen compiler/options/source.
        project = {'status': 'measured', 'components': [native_metrics(items[0][2][0], profiles)]}
    else:
        project = {'status': 'incomplete', 'components': [component(unavailable('At least one execution lacks a completed native collection'), unavailable('No stable branch mappings'))]}
    reason = inventory.get('change_scope', {}).get('reason', 'No frozen changed-line range')
    return {'tools': profile['tools'], 'scopes': {'project': project,
        'changed_files': unavailable(reason), 'changed_lines': unavailable(reason)}}

def main():
    global MAPPING
    if sys.argv[1] == 'probe-collect':
        probe_collect(sys.argv[2], sys.argv[3]); return 0
    if sys.argv[1] == 'probe-read':
        raw = Path(sys.argv[2]); print(json.dumps(normalized(raw/'probe-binary', sorted(raw.glob('*.profraw'))))); return 0
    if sys.argv[1] == '--check':
        runtime()
        print(json.dumps({'status': 'adapter-started', 'versions': {n: call([tool(n), '--version']).strip() for n in ('llvm-cov','llvm-profdata')}})); return 0
    op, request, response = sys.argv[1:]
    req = read(request); MAPPING = req.get('artifact_map', {})
    if op == 'run': return run(req, response)
    if op == 'verify-preparation': result = verify_preparation(req)
    elif op == 'finish': result = finish(req)
    elif op == 'verify-report': verify_report(req['report']); result = {'status': 'valid'}
    elif op == 'summarize': result = summarize(req)
    else: raise ValueError('Unknown operation: ' + op)
    write(response, result)
    return 0

if __name__ == '__main__':
    sys.exit(main())
