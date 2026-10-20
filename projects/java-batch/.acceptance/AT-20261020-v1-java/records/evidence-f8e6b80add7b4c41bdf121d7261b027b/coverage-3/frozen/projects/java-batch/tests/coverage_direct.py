"""Independent JaCoCo CLI reader; deliberately does not import the adapter."""
import hashlib, json, pathlib, subprocess, sys, xml.etree.ElementTree as ET
P=pathlib.Path
cfg=json.loads((P(__file__).parent/'coverage-tools.json').read_text())
raw=P(sys.argv[1]);scratch=P(sys.argv[2]);scratch.mkdir(parents=True,exist_ok=True)
jar=P(cfg['tools']['cli']['path'])
assert hashlib.sha256(jar.read_bytes()).hexdigest()==cfg['tools']['cli']['sha256']
assert (raw/'session.exec').stat().st_size>0
base=[cfg['java'],'-jar',str(jar)]
info=subprocess.run([*base,'execinfo',str(raw/'session.exec')],text=True,capture_output=True,check=True)
assert 'Session "' in info.stdout
xml=scratch/'direct.xml'
r=subprocess.run([*base,'report',str(raw/'session.exec'),'--classfiles',str(raw/'classes'),'--xml',str(xml),'--quiet'],text=True,capture_output=True,check=True)
sf=ET.parse(xml).getroot().find("./package[@name='benchmark']/sourcefile[@name='BatchReport.java']")
assert sf is not None
metrics={}
for name,kind in [('line','LINE'),('branch','BRANCH')]:
    counter=sf.find("counter[@type='%s']"%kind)
    if counter is None: metrics[name]={'status':'unavailable','reason':'JaCoCo supplied no '+kind+' counter'}
    else:
        covered=int(counter.get('covered')); missed=int(counter.get('missed'))
        metrics[name]={'status':'measured','covered':covered,'total':covered+missed}
print(json.dumps({'schema':'coverage-probe-normalized-v1','components':[{'id':'java-batch','source_paths':['projects/java-batch/src/main/java/benchmark/BatchReport.java'],'metrics':metrics}]}))
