"""Seal only this completed offline candidate; never materialize runtime identity."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('irq_adopt_freeze',HERE/'adopt.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);pins,_=m.sources()
need=m.need;sha=m.sha
test=json.loads((HERE/'test-result.json').read_bytes());need(test['passed'] is True and test['new_cases']==20,'actual new tests required')
results=[]
for flags,expected in [(['-B'],0),(['-B','-O'],1)]:
    argv=[sys.executable,*flags,str(HERE/'adopt.py')]
    child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();child.wait()
    need(child.returncode==expected,'default/optimized boundary differs')
    if expected==0:need(json.loads(stdout)['runtime_identity_or_request_created'] is False,'default runtime side effect')
    else:need(b'optimized interpreter is unsupported' in stderr,'wrong optimized rejection')
    results.append({'argv':argv,'pid':child.pid,'terminal':True,'returncode':child.returncode,
                    'stdout':stdout.decode(),'stderr':stderr.decode()})
(HERE/'default-result.json').write_text(json.dumps({'passed':True,'results':results,'device_accessed':False},indent=2)+'\n')
names=['README.md','adopt.py','adopt-device-tail.inc','source-pins.json','test-delta.py','test-result.json','default-result.json','freeze.py']
files={name:{'sha256':sha((HERE/name).read_bytes()),'bytes':(HERE/name).stat().st_size} for name in names}
delivery={'schema':'samurai-irq-cohort-adoption-offline-v1','passed':True,'frozen':True,'files':files,
    'source_inputs':pins,'actual_new_cases':20,'old_suites_rerun':False,'device_SSH_USB_SDK_accessed':False,
    'actual_runtime_request_guard_endpoint_created':False,'physical_latency_accepted':False}
need(not (HERE/'delivery.json').exists(),'already frozen; inspect instead')
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps({'passed':True,'delivery_sha256':sha((HERE/'delivery.json').read_bytes()),'actual_new_cases':20}))
