"""Project JaCoCo lifecycle; all executable units/counters come from JaCoCo."""
import hashlib, json, os, pathlib, subprocess, sys, tempfile, xml.etree.ElementTree as ET
P=pathlib.Path
HERE=P(__file__).resolve().parent
SOURCE='projects/java-batch/src/main/java/benchmark/BatchReport.java'
ROOT=HERE.parents[2]
CFG=json.loads((HERE/'coverage-tools.json').read_text())
TOOLS=[{'name':'JaCoCo','version':CFG['version'],'role':'JVM agent; CLI report, merge and source-file counters'}]
MAP={}
def sha(p): return hashlib.sha256(P(p).read_bytes()).hexdigest()
def resolve(p,h=None):
    p=str(p)
    if P(p).is_file() and (h is None or sha(p)==h): return P(p)
    a=MAP.get(p+'#'+h) if h else None
    a=a or MAP.get(p)
    if a:
        q=P(a['path']) if isinstance(a,dict) else P(a)
        if h and sha(q)!=h: raise ValueError('mapped bytes changed: '+p)
        return q
    return P(p)
def read(p): return json.loads(resolve(p).read_text())
def save(p,v):
    P(p).parent.mkdir(parents=True,exist_ok=True); P(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def ref(p): return {'path':str(p),'sha256':sha(p)}
def check(p,h):
    q=resolve(p,h)
    if sha(q)!=h: raise ValueError('frozen bytes changed: '+str(p))
    return q
def tool(n): return str(check(CFG['tools'][n]['path'],CFG['tools'][n]['sha256']))
def cli(*args):
    r=subprocess.run([CFG['java'],'-jar',tool('cli'),*map(str,args)],capture_output=True,text=True)
    if r.returncode: raise ValueError('JaCoCo failed: '+r.stderr+r.stdout)
    if 'does not match' in r.stdout+r.stderr or 'do not match' in r.stdout+r.stderr:
        raise ValueError('JaCoCo rejected mismatching execution/class bytes: '+r.stdout+r.stderr)
    return r.stdout
def unavailable(reason):
    return [{'id':'java-batch','label':'BatchReport.java (JaCoCo source-file counters)','source_paths':[SOURCE],**{k:{'status':'unavailable','reason':reason} for k in ('line','branch')}}]
def collection_status(components,complete):
    return 'measured' if complete and all(c[k]['status']=='measured' for c in components for k in ('line','branch')) else 'incomplete'
def parse_xml(path):
    doc=ET.parse(path).getroot(); sf=doc.find("./package[@name='benchmark']/sourcefile[@name='BatchReport.java']")
    if sf is None: raise ValueError('JaCoCo omitted frozen source')
    metrics={}
    for name,typ in [('line','LINE'),('branch','BRANCH')]:
        c=sf.find("counter[@type='%s']"%typ)
        if c is None: metrics[name]={'status':'unavailable','reason':'JaCoCo supplied no '+typ+' counter'}
        else: metrics[name]={'status':'measured','covered':int(c.attrib['covered']),'total':int(c.attrib['covered'])+int(c.attrib['missed'])}
    return [{'id':'java-batch','label':'BatchReport.java (JaCoCo source-file counters)','source_paths':[SOURCE],**metrics}]
def counters(execs,classes,scratch,complete=True):
    if not execs: return unavailable('No actual JVM snapshot; collection route did not start or dump was lost')
    for e in execs:
        if not P(e).is_file() or P(e).stat().st_size==0: return unavailable('Missing or empty native JVM snapshot')
        info=cli('execinfo',e)
        if 'Session "' not in info: raise ValueError('No real JaCoCo session in native snapshot')
    xml=P(scratch)/'jacoco.xml'
    cli('report',*execs,'--classfiles',classes,'--xml',xml,'--quiet')
    result=parse_xml(xml)
    if not complete:
        for c in result:
            for k in ('line','branch'):
                if c[k]['status']=='measured': c[k].update(status='incomplete',reason='Collection finalization was not completed')
    return result

def validate_profile(path):
    p=read(path); s=p['spec']; root=P(s['project_root'])
    assert p['schema']=='project-coverage-preparation-v1'
    runtime=read(check(s['runtime_manifest'],s['runtime_sha256']))
    probe=read(check(s['probe_report'],s['probe_report_sha256']))
    assert runtime['workspace']==str(root) and runtime['revision']==s['revision']
    # A relative registry changes meaning between host preparation and test cwd.
    # Reject it before activating collection rather than silently relocating it.
    registry=P(s['registry_path'])
    assert registry.is_absolute(), 'Coverage registry_path must be absolute'
    workflows=P(s['runtime_manifest']).resolve().parents[2]
    assert registry.parent.parent.resolve()==workflows, 'Coverage registry must use a dedicated workflow attempt directory'
    executables={e['name']:e for e in runtime['executables']}
    for name in ('java','javac'):
        assert P(CFG[name]).resolve()==P(executables[name]['resolved_path']).resolve(), 'Coverage executor differs from frozen runtime: '+name
    assert probe['runtime_sha256']==s['runtime_sha256']
    assert probe['workspace']==str(root) and probe['revision']==s['revision']
    assert probe['status']=='ready', 'Coverage probes are not ready'
    for n,h in {**s['source_hashes'],**p['adapter_files']}.items(): check(root/n,h)
    check(s['inventory_path'],s['inventory_sha256'])
    for e in p['preparation_evidence']: check(e['path'],e['sha256'])
    if not MAP:
        for e in runtime['executables']: check(e['resolved_path'],e['sha256'])
    for h in runtime.get('dependency_hashes',{}): check(root/h,runtime['dependency_hashes'][h])
    assert cli('version').strip()==CFG['version']
    tool('agent')
    return p

def compile_source(root,classes):
    P(classes).mkdir(parents=True,exist_ok=True)
    subprocess.run([CFG['javac'],'--release','17','-encoding','UTF-8','-d',str(classes),str(root/SOURCE)],check=True)

def execute(req,response):
    prof=validate_profile(P(req['prepared'])/'prepared.json')
    assert sha(P(req['prepared'])/'prepared.json')==req['prepared_sha256']
    assert req['cwd']==prof['spec']['project_root']
    out=P(req['output']); raw=out/'native'; raw.mkdir(exist_ok=False)
    compile_source(P(req['cwd']),raw/'classes')
    env=os.environ.copy(); env.update(req.get('env',{}))
    option='-javaagent:'+tool('agent')+'=destfile='+str(raw/'session.exec')+',append=true,includes=benchmark.*,dumponexit=true'
    if '-javaagent:' in env.get('JAVA_TOOL_OPTIONS',''): raise ValueError('Existing Java agent conflicts with frozen collector')
    env['JAVA_TOOL_OPTIONS']=(env.get('JAVA_TOOL_OPTIONS','')+' '+option).strip()
    state={'schema':'java-coverage-lifecycle-v1','command':req['command'],'scene_id':req['scene_id'],'prepared_sha256':req['prepared_sha256'],'request':ref(req['_path']),'complete':False}
    save(out/'collection.json',state)
    try:
        r=subprocess.run(req['command'],cwd=req['cwd'],env=env)
        state.update(exit_code=r.returncode,complete=r.returncode>=0)
    except BaseException as e:
        state['error']=str(e);save(out/'collection.json',state);raise
    save(out/'collection.json',state)
    save(response,{'exit_code':r.returncode,'collection':ref(out/'collection.json')})
    return r.returncode

def report_data(report):
    p=validate_profile(P(report['prepared'])/'prepared.json')
    for x in report['raw_evidence']: check(x['path'],x['sha256'])
    lifecycle=read(check(report['collection']['path'],report['collection']['sha256']))
    request=read(check(report['execution_request']['path'],report['execution_request']['sha256']))
    receipt=read(check(report['receipt_path'],report['execution_sha256']))
    assert lifecycle['command']==request['command'] and lifecycle['scene_id']==report['scene_id']==request['scene_id']
    assert lifecycle['prepared_sha256']==report['prepared_sha256']==request['prepared_sha256']
    assert receipt['coverage_session_sha256']==report['execution_request']['sha256']
    check(lifecycle['request']['path'],lifecycle['request']['sha256'])
    assert lifecycle['request']['sha256']==report['execution_request']['sha256']
    if lifecycle.get('complete'):
        assert lifecycle['exit_code']==receipt['exit_code'], 'Execution exit code differs from lifecycle'
    assert receipt['head_before']==receipt['head_after']==p['spec']['revision']
    expected=[*p['entry'],'run',receipt['coverage_session_path'],str(P(request['output'])/'run-response.json')]
    assert receipt['command']==expected
    execs=[str(check(x['path'],x['sha256'])) for x in report['raw_evidence'] if x.get('role')=='execution-data']
    with tempfile.TemporaryDirectory() as tmp:
        classes=P(tmp)/'classes'; classes.mkdir()
        for x in report['raw_evidence']:
            if x.get('role')=='classfile':
                q=classes/x['class_relative'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(check(x['path'],x['sha256']).read_bytes())
        cs=counters(execs,classes,tmp,lifecycle.get('complete',False))
    return p,cs,execs

def operation(op,req,response):
    global MAP
    MAP=req.get('artifact_map',{})
    if op=='verify-preparation': validate_profile(req['prepared']); return {'status':'valid'}
    if op=='run': return execute(req,response)
    if op=='finish':
        r=read(req['request']);p=read(P(r['prepared'])/'prepared.json'); out=P(req['output']); raw=out/'native'
        life=read(out/'collection.json') if (out/'collection.json').exists() else {'complete':False,'command':r['command'],'scene_id':r['scene_id'],'prepared_sha256':r['prepared_sha256'],'reason':'No lifecycle start recorded','request':ref(req['request'])}
        if not (out/'collection.json').exists(): save(out/'collection.json',life)
        files=[]
        for x in sorted(raw.rglob('*')):
            if x.is_file():
                f=ref(x)
                if x.suffix=='.exec': f['role']='execution-data'
                elif x.suffix=='.class':f.update(role='classfile',class_relative=str(x.relative_to(raw/'classes')))
                files.append(f)
        with tempfile.TemporaryDirectory() as tmp: cs=counters([x['path'] for x in files if x.get('role')=='execution-data'],raw/'classes',tmp,life.get('complete',False))
        return {'schema':'project-tool-coverage-report-v1','protocol':'project-coverage-v1','prepared':r['prepared'],'prepared_sha256':r['prepared_sha256'],'scene_id':r['scene_id'],'revision':p['spec']['revision'],'source_hashes':p['spec']['source_hashes'],'tools':p['tools'],'collection_relation':'same_run','status':collection_status(cs,life.get('complete',False)),'receipt_path':req['receipt'],'execution_sha256':sha(req['receipt']),'raw_evidence':files,'components':cs,'collection':ref(out/'collection.json'),'execution_request':ref(req['request'])}
    if op=='verify-report':
        r=read(req['report']);p,cs,_=report_data(r); assert cs==r['components'],'Native counters differ'
        lifecycle=read(check(r['collection']['path'],r['collection']['sha256']))
        assert r['status']==collection_status(cs,lifecycle.get('complete',False))
        return {'status':'valid'}
    if op=='summarize':
        reports=[read(x) for x in req['reports']];assert len({r['prepared_sha256'] for r in reports})==1
        execs=[];incomplete=False
        for r in reports:
            p,cs,es=report_data(r);assert cs==r['components'];execs+=es;incomplete|=r['status']!='measured'
        assert req['inventory']==read(p['spec']['inventory_path'])
        with tempfile.TemporaryDirectory() as tmp:
            classes=P(tmp)/'classes'; classes.mkdir()
            for x in reports[0]['raw_evidence']:
                if x.get('role')=='classfile':
                    dest=classes/x['class_relative'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(check(x['path'],x['sha256']).read_bytes())
            if execs:
                merged=P(tmp)/'merged.exec';cli('merge',*execs,'--destfile',merged,'--quiet'); execs=[str(merged)]
            cs=counters(execs,classes,tmp,not incomplete)
        return {'tools':p['tools'],'scopes':{'project':{'status':'incomplete' if incomplete else 'measured','components':cs},**{s:{'status':'unavailable','reason':'Requirements baseline inventory has no code diff; changed scope is undefined'} for s in ('changed_files','changed_lines')}}}
    raise ValueError('Unknown operation: '+op)

if __name__=='__main__':
    try:
        if sys.argv[1:] == ['--self-check']:
            assert cli('version').strip()==CFG['version'];tool('agent');print(json.dumps({'status':'valid','version':CFG['version']}));sys.exit(0)
        op,inp,out=sys.argv[1:]; req=read(inp);req['_path']=str(P(inp).resolve());result=operation(op,req,out)
        if op=='run': sys.exit(result)
        save(out,result)
    except Exception as e:
        print(str(e),file=sys.stderr);sys.exit(1)
