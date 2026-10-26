"""Only the new source-version/stage binding in actual operator context validation."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
o=load('actual_current_context_operator',HERE/'fastboot-operator.py')
contract=json.loads((HERE/'prepare-contract.json').read_bytes());sha=lambda data:hashlib.sha256(data).hexdigest()
tx='irq-native-usb-pm-activate-context-fixture';boot='11111111-2222-4333-8444-555555555555';token='a'*48
ident=dict(boot_id=boot,serial_sha256='b'*64,compatible_sha256='c'*64,rootfs_sha256='d'*64)
stage={'fixture':'model of the separately tested actual stage boundary'}
adoption={'transaction_id':'usb-irq-protection-activate-context-fixture','guard_path':'/var/lib/samurai/usb-irq-protection-activate-context-fixture-adopted/boot-id-private.txt','guard_sha256':'e'*64}
source={'fixture':'original runtime evidence modeled at this boundary'}
calls=[]
review=dict(stage=stage,source_review_inputs=source,request={'identity':ident,'adoption':adoption})
proof=SimpleNamespace(review_stage=lambda *args:calls.append(args) or copy.deepcopy(review),guard_stage_fields=lambda value:value['stage'])
spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
cases=[]
with tempfile.TemporaryDirectory() as top:
 root=Path(top)/tx;root.mkdir();remote='/root/charging-management-20261023/'+tx
 tools=Path(top)/'exact-worker-tools';tools.mkdir();o.ACTIVATION=tools
 for name in ['prepare-contract.json','eud-restart.py']:(tools/name).write_bytes((HERE/name).read_bytes())
 (tools/'activation-pins.json').write_text(json.dumps({name:sha((tools/name).read_bytes()) for name in ['prepare-contract.json','eud-restart.py']}))
 qargv=['python3','-B',remote+'/eud-quiesce.py','--guard',remote+'/guard-private.json','--commit-quiesce']
 rargv=['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader']
 def save(name,value):
  raw=(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode());(root/name).write_bytes(raw)
  return {'path':name,'sha256':sha(raw)}
 guard=dict(contract['fixed_guard_fields'],transaction_id=tx,token=token,boot_id=boot,soc_serial_sha256=ident['serial_sha256'],
  compatible_sha256=ident['compatible_sha256'],rootfs_release_sha256=ident['rootfs_sha256'],stage=stage,adoption=adoption)
 g=save('guard-private.json',guard);common=dict(transaction_id=tx,token=token,boot_id=boot)
 files={'guard':g,'quiesce_state':save('state-private.json',dict(common,pid=111,terminal=True,exit_code=0)),
  'quiesce_summary':save('summary.json',dict(common,taint=0)), 'quiesce_boot_id':save('boot-id-private.txt',(boot+'\n').encode()),
  'quiesce_process':save('process-private.json',dict(common,pid=111,startticks=123,argv=qargv,status='absent'))}
 rc=dict(common,schema='samurai-eud-restart-host-claim-v1',guard_sha256=g['sha256'],request_count=1,worker_sha256=sha((HERE/'eud-restart.py').read_bytes()),argv=rargv)
 files['restart_claim']=save('restart-claim-private.json',rc)
 rd=dict(rc,schema='samurai-eud-restart-dispatch-v1',host_claim_sha256=files['restart_claim']['sha256'],
  state='dispatched_once',restart_claim_intent='claimed_by_pinned_worker',host_process={'pid':222,'startticks':456,'argv':['ssh','fixture'], 'terminal':True,'returncode':255})
 files['restart_dispatch']=save('restart-dispatch-private.json',rd)
 context=dict(schema='samurai-irq-native-usb-pm-fastboot-context-v1',transaction_id=tx,token=token,old_boot_id=boot,
  guard_sha256=g['sha256'],files=files,stage_directory='fixture-stage',stage_fetch_directory='fixture-fetch',source_review_inputs=source)
 path=root/'host-context-private.json'
 def validate(value):
  save(path.name,value)
  with patch('importlib.util.spec_from_file_location',return_value=spec),patch('importlib.util.module_from_spec',return_value=proof):return o.validate_context(path)
 assert validate(context)==context and calls==[('fixture-stage','fixture-fetch')]
 cases.append('actual seven-file context, current502 source/504 target and stage proof accepted')
 for label,change in [('different completed runtime source',lambda value:value.update(source_review_inputs={'different':True})),
                      ('legacy context schema',lambda value:value.update(schema='samurai-image502-notify-fastboot-context-v1'))]:
  value=copy.deepcopy(context);change(value)
  try:validate(value)
  except ValueError:cases.append('rejected '+label)
  else:raise AssertionError(label)
 changed_guard=dict(guard,source_kernel_version='#501 old')
 value=copy.deepcopy(context);value['files']['guard']=save('guard-private.json',changed_guard);value['guard_sha256']=value['files']['guard']['sha256']
 try:validate(value)
 except ValueError:cases.append('rejected old source even with internally consistent guard hash')
 else:raise AssertionError('old source accepted')
report=dict(passed=True,cases=cases,tested_files={name:sha((HERE/name).read_bytes()) for name in ['fastboot-operator.py','test-context.py']},
 stage_boundary_modeled=True,actual_context_validation_function_used=True,device_accessed=False,materialized_bundle_changed=False)
(HERE/'context-test-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(cases),'device_accessed':False}))
