"""Authenticate past source originals without consulting the mutable current pointer."""
from pathlib import Path
from types import SimpleNamespace
import ast,copy,hashlib,importlib.util,inspect,json,re,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def need(value,message):
 if not value:raise ValueError(message)
def local(value):
 text=str(value).replace('\\','/')
 if sys.platform!='win32' and re.match(r'^[A-Za-z]:/',text):text='/mnt/'+text[0].lower()+text[2:]
 return Path(text).resolve()
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,local(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def source_check():
 pins=json.loads((HERE/'source-pins.json').read_bytes())
 for name,row in pins.items():
  raw=local(row['path']).read_bytes();need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],'frozen source changed: '+name)
 for delivery,source,filename in [('runtime_delivery','runtime_review','update-review.py'),
  ('stage_host_delivery','stage_host','host.py'),('device_delivery','stage_proof','stage-proof.py')]:
  report=json.loads(local(pins[delivery]['path']).read_bytes())
  need(report['passed'] is True and report['files'][filename]['sha256']==pins[source]['sha256'],'frozen source/delivery differs: '+source)
 return pins

def reconcile_historical_base(replayed,original,current_pointer_path):
 """Normalize only the historical pointer's former location, never its bytes."""
 expected=original['files']['current_pointer'];retained=replayed['files']['current_pointer']
 need(set(expected)==set(retained)=={'path','sha256'} and local(expected['path'])==local(current_pointer_path),
  'original recorded current-pointer location differs')
 need(local(retained['path'])==local(replayed['files']['pointer']['path']) and
  expected['sha256']==retained['sha256']==replayed['files']['pointer']['sha256'],
  'retained actual pointer bytes do not match original adoption')
 normalized=copy.deepcopy(replayed);normalized['files']['current_pointer']=copy.deepcopy(expected)
 need(normalized==original,'retained adoption differs beyond historical pointer location')
 return normalized,copy.deepcopy(retained)

def retained_base_review(runtime_module,inputs,original):
 base=runtime_module.base_module()
 source=inspect.getsource(base.review_adoption)
 # Preserve the complete original postboot, exact executed adoption, true child
 # wait, reply and pointer-content checks. Only the read location changes.
 old="'current_pointer': BASE / 'boot-adoption-private.json'"
 new="'current_pointer': folder / 'adoption-pointer-private.json'"
 need(source.count(old)==1,'original adoption reviewer shape changed')
 namespace=dict(base.__dict__)
 exec(compile(source.replace(old,new),'<retained-original-adoption-review>','exec'),namespace)
 replayed=namespace['review_adoption'](**inputs)
 return reconcile_historical_base(replayed,original,base.BASE/'boot-adoption-private.json')

def review_retained_runtime(runtime_pins):
 pins=source_check();path=local(runtime_pins);saved=json.loads(path.read_bytes())
 need(saved.get('schema')=='samurai-icon-irq-runtime-update-v1','actual original completed runtime overlay required')
 runtime=load(pins['runtime_review']['path'],'retained_actual_runtime_review')
 inputs=saved['review_inputs'];update=local(inputs['update_directory'])
 upins,_=runtime.check_sources()
 update_host=load(runtime.REF/upins['update_host']['path'],'retained_original_update_host')
 out,binding,request,request_raw,_=update_host.bound(update.parent.name)
 need(local(out)==update.parent,'one original completed update fetch')
 base,retained_pointer=retained_base_review(runtime,inputs['base_adoption'],binding['reviewed'])
 # base carries the original historical path fact so the unchanged update
 # reviewer can compare its original binding. It is not a current-pointer read.
 checked=runtime.review_update(update,base)
 need(checked==saved['reviewed'] and checked['review_inputs']==inputs and checked['manifest_sha256']==runtime.NEW,
  'retained completed runtime evidence differs')
 files={name:copy.deepcopy(row) for name,row in checked['files'].items() if name!='current_pointer'}
 files['retained_current_pointer']=retained_pointer
 files['runtime_overlay']={'path':str(path),'sha256':sha(path.read_bytes())}
 for name,row in files.items():need(sha(local(row['path']).read_bytes())==row['sha256'],'retained source bytes changed: '+name)
 return {'schema':'samurai-irq-native-usb-pm-retained-runtime-review-v1','runtime':checked,'base_adoption':base,
  'files':files,'historical_current_pointer_location':checked['files']['current_pointer']['path'],
  'current_pointer_consulted':False,'current_device_identity_or_health_verified':False,
  'device_accessed':False,'runtime_request_created':False}

def retained_stage_bound(host,transaction):
 out,binding,request,raw,pins=host.bound(transaction,launching=False)
 path=local(binding['runtime_pins']['path'])
 need(sha(path.read_bytes())==binding['runtime_pins']['sha256'],'actual original runtime overlay changed')
 source=review_retained_runtime(path)
 need(source['runtime']==binding['reviewed'] and source['base_adoption']['adoption']==binding['source_adoption'] and
  source['runtime']['review_inputs']==binding['source_review_inputs'],'actual stage source/runtime differs')
 expected=host.make_request(transaction,source['base_adoption'],pins['worker']['sha256'],
  local(pins['payload']['path']).read_bytes())
 expected['lease_token']=request['lease_token']
 need(expected==request,'actual stage request not derived from retained source')
 worker=host.load(pins['worker']['path'],'retained_stage_pure_request_contract');worker.unpack(request)
 return (out,binding,request,raw,pins),source

def review_retained_stage(stage_directory,fetch_directory):
 pins=source_check();host=load(pins['stage_host']['path'],'retained_original_current_stage_host')
 proof=load(pins['stage_proof']['path'],'retained_original_current_stage_proof')
 original_load=proof.load;captured=[]
 def bound(transaction,*,launching=False):
  values,source=retained_stage_bound(host,transaction);captured.append(source);return values
 wrapped=SimpleNamespace(**vars(host));wrapped.bound=bound
 def retained_load(path,name):
  if local(path)==local(pins['stage_host']['path']):return wrapped
  return original_load(path,name)
 proof.load=retained_load
 reviewed=proof.review_stage(stage_directory,fetch_directory)
 need(len(captured)==1 and reviewed['source_runtime']==captured[0]['runtime'],'one original source stage review')
 # Original fetch/source checks and actual stage result/snapshots/terminals are
 # unchanged. Only host.bound's obsolete current-pointer dependency is replaced.
 return {'schema':'samurai-irq-native-usb-pm-retained-stage-review-v1','stage_review':reviewed,
  'source_runtime_review':captured[0],'current_pointer_consulted':False,
  'current_device_identity_or_health_verified':False,'runtime_request_created':False,'device_accessed':False}

if __name__=='__main__':
 source_check();print(json.dumps({'source_only':True,'current_pointer_consulted':False,'device_accessed':False,'runtime_request_created':False}))
