"""Derive only original saved-command review and read-only current probe."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
WORKER=HERE.parent/'irq-native-usb-pm-cold-rollback-candidate'
DEVICE=HERE.parent/'irq-native-usb-pm-activation-device-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def functions(path):
 text=path.read_text();tree=ast.parse(text)
 return text,tree,{n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
def write(name,text):
 path=HERE/name;assert not path.exists(),name;path.write_text(text,encoding='utf-8',newline='\n')
def main():
 assert sys.argv[1:]==['--prepare'],'explicit local generation only'
 assert sha((WORKER/'delivery.json').read_bytes())=='d43e1e7153a4b9d1c5dd8a27437ff571713f6fbf2cb4d555a6f091e25f9cde97'
 original=REF/'charging-oem-audit-20261023/usb-irq-protection-fastboot-candidate/completion-proof.py'
 old,_,func=functions(original)
 assert sha(original.read_bytes())=='d4a7b29c3f5978c1254c4b7c40376fbf12453057d4ba8cc98cbb4ef7a952be00'
 header='''"""Read saved source and exact original logdump commands. No USB dispatch."""
from pathlib import Path
from types import SimpleNamespace
import copy,hashlib,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_rollback_shared',HERE/'shared.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
need=shared.need;local=shared.local;load_module=shared.load;source_check=shared.source_check
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
read_json=lambda path:json.loads(Path(path).read_bytes())
load=read_json
OPERATOR_PATH=HERE.parent/'irq-native-usb-pm-activation-device-candidate/fastboot-operator.py'
'''
 action=func['review_action'].replace('samurai-usb-irq-protection-fastboot-action-v1','samurai-irq-native-usb-pm-fastboot-action-v1').replace("sha(HERE/'fastboot-operator.py')","sha(OPERATOR_PATH)")
 write('saved-proof.py',header+func['saved_command']+'\n\n'+action+'\n\n'+(HERE/'saved-body.py.inc').read_text()+
  "\nif __name__=='__main__':\n source_check();print(json.dumps({'source_only':True,'device_accessed':False,'runtime_request_created':False}))\n")
 wtext,wt,wfunc=functions(WORKER/'restore-worker.py')
 constants={}
 wanted={'OLD_NOTES','NEW_NOTES','VERSION502','VERSION504','RELEASE','BOOT','LOGDUMP502','LOGDUMP504','PROFILES','INSTANCE'}
 for node in wt.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in wanted:
   constants[node.targets[0].id]=ast.literal_eval(node.value)
 base=next(n for n in wt.body if isinstance(n,ast.ClassDef) and n.name=='BaseDevice')
 current=next(n for n in wt.body if isinstance(n,ast.ClassDef) and n.name=='Device')
 def method(tree,name):
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
  return '    '+ast.get_source_segment(wtext,node)+'\n'
 probe='''"""Read-only current kernel/carriers/notes/cache. Default does not access a device."""
from pathlib import Path
import base64,hashlib,json,os,re,stat,struct,sys,time
sys.dont_write_bytecode=True
'''+ '\n'.join(name+'='+repr(value) for name,value in constants.items())+'\n\n'
 for name in ['need','sha','read_owned','expected_profile','validate_cache']:probe+=wfunc[name]+'\n\n'
 probe+='class Probe:\n'+'''    def __init__(self,request):
        self.request=request;self.carriers=None;self.mac_fd=None;self.baseline=None
'''+method(current,'identity')+method(base,'block_fact')+method(base,'current')
 cache=method(current,'cache_evidence').replace("validate_cache(value);need(value==self.request['current_cache'],'current cache/instance continuously retained')",
  "validate_cache(value);need(self.baseline is None or value==self.baseline,'same current cache throughout read-only bracket')")
 probe+=cache+'''    def open_cache(self):
        p=Path(INSTANCE)
        need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
        self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        self.baseline=self.cache_evidence()
    def close(self):
        if self.mac_fd is not None:
            try:os.close(self.mac_fd)
            finally:self.mac_fd=None

def collect(request,probe):
    need(request['schema']=='samurai-irq-native-usb-pm-rollback-current-probe-v1','current probe schema')
    start=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    try:
        before=probe.identity();probe.open_cache();cache_before=probe.cache_evidence()
        current=probe.current(request);current['current_cache']=probe.cache_evidence()
        after=probe.identity();cache_after=probe.cache_evidence()
        need(before==current['identity']==after and cache_before==current['current_cache']==cache_after,'current identity/cache bracket')
        return dict(schema=request['schema'],request=request,identity_before=before,current=current,identity_after=after,
            cache_before=cache_before,cache_after=cache_after,started_boottime_ns=start,
            ended_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
    finally:probe.close()

def main(request=None):
    if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
    if request is None:print(json.dumps({'source_only':True,'device_accessed':False}));return 0
    need(set(request)=={'schema','new_endpoint','profile','saved_source_binding_sha256'} and request['profile'] in PROFILES,
        'explicit source-bound current probe')
    print(json.dumps(collect(request,Probe(request))),flush=True);return 0
if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
'''
 compile(probe,'current-probe.py','exec');write('current-probe.py',probe)
 entries={
  'worker':WORKER/'restore-worker.py','worker_delivery':WORKER/'delivery.json',
  'retained':HERE.parent/'irq-native-usb-pm-retained-source-candidate/reviewer.py',
  'retained_delivery':HERE.parent/'irq-native-usb-pm-retained-source-candidate/delivery.json',
  'operator':DEVICE/'fastboot-operator.py','device_delivery':DEVICE/'delivery.json',
  'completion_method':original,
  'auth_host':REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/host.py',
  'auth_delivery':REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/delivery.json',
  'probe':HERE/'current-probe.py'}
 payload=Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01/rollback-7cb-18e8-payload.tar.gz')
 if sys.platform!='win32':payload=Path('/mnt/e/'+str(payload).replace('\\','/')[3:])
 entries['payload']=payload
 pins={name:{'path':str(path.resolve()),'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size} for name,path in entries.items()}
 write('source-pins.json',json.dumps(pins,indent=2)+'\n')
 write('source-reuse.json',json.dumps(dict(passed=True,saved_command_byte_exact=True,
  review_action_changes='current action schema and pinned operator source path only',
  exact_probe_helpers=['need','sha','read_owned','expected_profile','validate_cache'],
  exact_probe_methods=['identity','block_fact','current'],
  cache_method_change='only replace expected-request cache with captured readonly baseline',
  old_completion_source_sha256=sha(original.read_bytes()),device_accessed=False),indent=2)+'\n')
 print(json.dumps({'prepared':True,'device_accessed':False,'runtime_request_created':False}))
if __name__=='__main__':main()
