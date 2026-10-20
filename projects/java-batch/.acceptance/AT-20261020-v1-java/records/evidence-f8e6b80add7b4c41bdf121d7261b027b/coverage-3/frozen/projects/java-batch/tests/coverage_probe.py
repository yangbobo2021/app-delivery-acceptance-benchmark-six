"""Host-run isolated probes and adapter read path. No business scenarios."""
import json, os, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode=True
import coverage_adapter as a
P=pathlib.Path

def collect(mode,raw,probe,route="java-cli"):
    raw=P(raw);probe=P(probe);probe.mkdir(parents=True,exist_ok=True)
    a.compile_source(a.ROOT,raw/'classes')
    helpers=probe/'helper-classes';helpers.mkdir(exist_ok=True)
    subprocess.run([a.CFG['javac'],'--release','17','-d',str(helpers),str(a.HERE/'CoverageProbe.java')],check=True)
    cmd=[a.CFG['java'],'-cp',str(helpers)+':'+str(raw/'classes'),'CoverageProbe']
    env=os.environ.copy()
    env['JAVA_TOOL_OPTIONS']='-javaagent:'+a.tool('agent')+'=destfile='+str(raw/'session.exec')+',append=true,includes=benchmark.*,dumponexit=true'
    if mode=='nonzero':cmd+=['initialize']
    if route=='python-subprocess':
        cmd=[sys.executable,'-c','import subprocess,sys; sys.exit(subprocess.run(sys.argv[1:]).returncode)',*cmd]
    r=subprocess.run(cmd,capture_output=True,text=True,env=env)
    a.save(probe/'collect-receipt.json',{'command':cmd,'env':{'JAVA_TOOL_OPTIONS':env['JAVA_TOOL_OPTIONS']},'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    if r.returncode:raise ValueError('JVM probe failed')
    # Real failure paths: no JVM started, and a JVM which suppresses its exit dump.
    failure=probe/'failure-paths';failure.mkdir(exist_ok=True)
    for name,argv in [('route-not-started',[sys.executable,'-c','pass']),('no-exit-snapshot',[a.CFG['java'],'-javaagent:'+a.tool('agent')+'=destfile='+str(failure/'lost.exec')+',dumponexit=false','-cp',str(helpers),'CoverageProbe'])]:
        result=subprocess.run(argv,capture_output=True,text=True)
        snapshot=failure/('never-started.exec' if name=='route-not-started' else 'lost.exec')
        metrics=a.counters([snapshot],raw/'classes',failure)
        assert all(c[k]['status']=='unavailable' for c in metrics for k in ('line','branch'))
        assert not any('covered' in c[k] for c in metrics for k in ('line','branch'))
        a.save(failure/(name+'.json'),{'command':argv,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'snapshot_path':str(snapshot),'snapshot_exists':snapshot.exists(),'snapshot_bytes':snapshot.stat().st_size if snapshot.exists() else None,'report_status':a.collection_status(metrics,True),'components':metrics})
        assert result.returncode==0
        assert a.collection_status(metrics,True)=='incomplete'
    # JaCoCo file output opens destfile even when dumponexit=false. An empty
    # placeholder is not a snapshot and must not become a measured zero baseline.
    assert not (failure/'lost.exec').exists() or (failure/'lost.exec').stat().st_size==0
    # A valid snapshot with unfinished lifecycle must retain incomplete state.
    cs=a.counters([raw/'session.exec'],raw/'classes',failure,complete=False)
    assert all(c[k]['status']=='incomplete' for c in cs for k in ('line','branch'))
    assert a.collection_status(cs,False)=='incomplete'
    a.save(failure/'unfinished-finalization.json',{'complete':False,'snapshot':a.ref(raw/'session.exec'),'report_status':a.collection_status(cs,False),'components':cs})
    # Corrupt native input must be rejected by the actual tool, never zero-filled.
    bad=failure/'corrupt.exec';bad.write_bytes(b'not a JaCoCo snapshot')
    try:a.counters([bad],raw/'classes',failure)
    except Exception as e:a.save(failure/'corrupt-native-rejected.json',{'status':'rejected','error':str(e),'native':a.ref(bad)})
    else:raise ValueError('Corrupt native data accepted')

def main():
    op=sys.argv[1]
    if op=='collect':collect(*sys.argv[2:]);return
    raw=P(sys.argv[2]); scratch=P(sys.argv[3]);scratch.mkdir(parents=True,exist_ok=True)
    cs=a.counters([raw/'session.exec'],raw/'classes',scratch)
    print(json.dumps({'schema':'coverage-probe-normalized-v1','components':[{'id':c['id'],'source_paths':c['source_paths'],'metrics':{k:c[k] for k in ('line','branch')}} for c in cs]}))
if __name__=='__main__':main()
