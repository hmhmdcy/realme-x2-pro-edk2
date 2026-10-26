"""Changed boot-only dispatch/context functions. All USB/auth/process boundaries fake.
Temporary fixture context is not a runtime binding or real future guard.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,tempfile,types
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
spec=importlib.util.spec_from_file_location('irq_boot_operator_under_test',HERE/'fastboot-operator.py')
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
names=[]
def case(name):names.append(name)
def reject(call):
 try:call()
 except (ValueError,KeyError,FileNotFoundError,AssertionError):return
 raise AssertionError('expected rejection')
def put(path,value):path.write_text(json.dumps(value));return {'path':path.name,'sha256':sha(path)}
original_images,original_sizes,original_windows=o.IMAGES,o.SIZES,o.windows_path
with tempfile.TemporaryDirectory() as td:
 root=Path(td);candidate=root/'candidate.img';original=root/'original.img'
 candidate.write_bytes(b'N'*96);original.write_bytes(b'O'*96)
 o.IMAGES={'candidate':{'boot':(candidate,sha(candidate),96)},'original':{'boot':(original,sha(original),96)}}
 o.SIZES={'boot':96,'logdump':64};o.windows_path=lambda p:'FIXTURE:'+p.name
 calls=[];mode={}
 def call(label,argv):
  calls.append((label,argv))
  if label=='devices':return mode.get('devices','SERIAL fastboot\n'),''
  if label=='product':return '',mode.get('product','product: msmnile\n')
  if label.endswith('-size'):
   part=label.removesuffix('-size');return '',f'partition-size:{part}: {mode.get(part+"_size",o.SIZES[part])}\n'
  if label=='flash-boot':return '',mode.get('flash',"Writing 'boot' OKAY\n")
  if label=='reboot':return '',mode.get('reboot','')
  raise AssertionError((label,argv))
 for action,file in [('flash-candidate',candidate),('rollback-original',original)]:
  calls.clear();report=o.run_action(action,'SERIAL',call)
  assert report['partitions_written']==['boot'] and report['boot_complete'] is True
  assert report['unchanged_logdump_sha256']==o.LOGDUMP502 and report['rootfs_rollback_proven'] is False
  writes=[argv for _,argv in calls if 'flash' in argv]
  assert len(writes)==1 and writes[0][-3:]==['flash','boot','FIXTURE:'+file.name]
  assert [name for name,_ in calls][:4]==['devices','product','boot-size','logdump-size']
  case(action+' only exact boot after fresh identity and both geometry checks')
 calls.clear();assert o.run_action('inspect','SERIAL',call)['partitions_written']==[]
 assert not any('flash' in argv or 'reboot' in argv for _,argv in calls);case('inspect no write or reboot')
 for key,value in [('devices','SERIAL fastboot\nOTHER fastboot\n'),('devices','OTHER fastboot\n'),
                   ('product','product: wrong\n'),('boot_size',95),('logdump_size',63)]:
  mode[key]=value;calls.clear();reject(lambda:o.run_action('flash-candidate','SERIAL',call))
  assert not any('flash' in argv for _,argv in calls);mode.clear();case('reject '+key+' '+str(value).strip())
 pair=o.IMAGES['candidate'];o.IMAGES['candidate']={**pair,'logdump':(candidate,sha(candidate),96)}
 calls.clear();reject(lambda:o.run_action('flash-candidate','SERIAL',call));assert not any('flash' in argv for _,argv in calls)
 o.IMAGES['candidate']=pair;case('reject extra logdump write scope')
 candidate.write_bytes(b'changed');calls.clear();reject(lambda:o.run_action('flash-candidate','SERIAL',call))
 assert not any('flash' in argv for _,argv in calls);candidate.write_bytes(b'N'*96);case('changed actual carrier before dispatch rejected')
 mode['flash']="Writing 'logdump' OKAY\n";reject(lambda:o.run_action('flash-candidate','SERIAL',call));mode.clear()
 case('wrong partition confirmation never successful boot write')
 for action in o.REBOOT_IMAGES:
  calls.clear();report=o.run_action(action,'SERIAL',call)
  assert report['boot_success_proven'] is False and report['reboot_command_returned_zero'] is True
  assert len([argv for _,argv in calls if 'reboot' in argv])==1
  case(action+' remains runtime-unverified')
 directory=root/'actions';directory.mkdir();flash=directory/'flash-candidate';flash.mkdir()
 (flash/'request-private.json').write_text('{}')
 good={'claimed_ns':1,'action':'flash-candidate','passed':True,'terminal':True,'commands_terminal':True,
       'partitions_written':['boot'],'boot_complete':True,'flashed_images_sha256':o.image_hashes('candidate'),
       'unchanged_logdump_sha256':o.LOGDUMP502}
 result=flash/'result-private.json';put(result,good)
 assert o.reboot_binding(directory,'reboot-candidate')['image_result_sha256']==sha(result);case('reboot binds last exact candidate boot receipt')
 for edit in [dict(partitions_written=['logdump']),dict(commands_terminal=False),dict(boot_complete=False),
              dict(unchanged_logdump_sha256='f'*64),dict(passed=False)]:
  put(result,{**good,**edit});reject(lambda:o.reboot_binding(directory,'reboot-candidate'));case('reject reboot result '+next(iter(edit)))
 put(result,good);rollback=directory/'rollback-original';rollback.mkdir();(rollback/'request-private.json').write_text('{}')
 put(rollback/'result-private.json',{**good,'action':'rollback-original','claimed_ns':2,'passed':False})
 reject(lambda:o.reboot_binding(directory,'reboot-candidate'));case('later failed rollback prevents candidate reboot')
o.IMAGES,o.SIZES,o.windows_path=original_images,original_sizes,original_windows

# Test actual context comparison with explicit fake stage-proof and source gates.
# review_stage itself has separate author tests and is never invoked here.
saved={name:getattr(o,name) for name in ['source_inputs','stage_module','pinned_tools']}
o.source_inputs=lambda:{}
o.pinned_tools=lambda:{'eud-restart.py':'e'*64}
with tempfile.TemporaryDirectory() as td:
 tx='usb-irq-protection-activate-fixture-0001';base=Path(td)/tx;base.mkdir()
 boot='11111111-2222-3333-4444-555555555555';token='a'*48
 identity={'boot_id':boot,'version':'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',
           'serial_sha256':'1'*64,'compatible_sha256':'2'*64,'rootfs_sha256':'3'*64}
 stage_fields={'transaction_id':'usb-irq-protection-stage-fixture-0001','request_sha256':'4'*64,
               'result_sha256':'5'*64,'host_binding_sha256':'6'*64,'worker_sha256':'7'*64,'supervisor_sha256':'8'*64,'evidence':{}}
 adoption={'transaction_id':'image502-notify-live-001','guard_path':'/var/lib/samurai/FIXTURE/boot-id-private.txt',
           'guard_sha256':'9'*64,'postboot_raw_sha256':'b'*64,'actual_fresh_validation_sha256':'c'*64}
 reviewed={'source_boot_id':boot,'source_version':identity['version'],'identity':identity,'adoption':adoption}
 proof=types.SimpleNamespace(review_stage=lambda *args,**kwargs:copy.deepcopy(reviewed),guard_stage_fields=lambda review:copy.deepcopy(stage_fields))
 o.stage_module=lambda:proof
 fixed={'partitions':['boot'],'candidate_boot_sha256':o.IRQ_BOOT,'rollback_boot_sha256':o.ORIGINAL_BOOT,
        'unchanged_logdump_sha256':o.LOGDUMP502}
 contract={'schema':'samurai-usb-irq-protection-activation-contract-v1','fixed_guard_fields':fixed}
 guard={**fixed,'schema':'samurai-usb-irq-protection-activation-v1','transaction_id':tx,'token':token,'boot_id':boot,
        'kernel_version':identity['version'],'rootfs_release_sha256':identity['rootfs_sha256'],
        'soc_serial_sha256':identity['serial_sha256'],'compatible_sha256':identity['compatible_sha256'],
        'stage':copy.deepcopy(stage_fields),'adoption':{k:v for k,v in adoption.items() if k!='actual_fresh_validation_sha256'}}
 guard['adoption']['fresh_validation_sha256']=adoption['actual_fresh_validation_sha256']
 remote='/root/charging-management-20261023/'+tx
 common={'transaction_id':tx,'token':token,'boot_id':boot}
 fixtures={
  'guard':guard,'quiesce_state':{**common,'pid':42,'terminal':True,'exit_code':0},
  'quiesce_summary':{**common,'taint':0},
  'quiesce_process':{**common,'pid':42,'startticks':100,'status':'absent',
    'argv':['python3','-B',remote+'/eud-quiesce.py','--guard',remote+'/guard-private.json','--commit-quiesce']}}
 fixtures['restart_claim']={**common,'schema':'samurai-eud-restart-host-claim-v1','request_count':1,
   'worker_sha256':'e'*64,'argv':['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader']}
 fixtures['restart_dispatch']={**fixtures['restart_claim'],'schema':'samurai-eud-restart-dispatch-v1',
   'state':'dispatched_once','restart_claim_intent':'claimed_by_pinned_worker',
   'host_process':{'pid':43,'startticks':110,'argv':['FIXTURE-SSH'],'terminal':True,'returncode':255}}
 context={'schema':'samurai-usb-irq-protection-fastboot-context-v1','transaction_id':tx,'token':token,'old_boot_id':boot,
          'stage_directory':'FIXTURE-HOST-STAGE','stage_fetch_directory':'FIXTURE-FETCH'}
 def write_context():
  paths={name:put(base/(name+'-private.json'),value) for name,value in fixtures.items() if name not in ['restart_claim','restart_dispatch']}
  digest=paths['guard']['sha256']
  for name in ['restart_claim','restart_dispatch']:fixtures[name]['guard_sha256']=digest
  paths['restart_claim']=put(base/'restart-claim-private.json',fixtures['restart_claim'])
  fixtures['restart_dispatch']['host_claim_sha256']=paths['restart_claim']['sha256']
  paths['restart_dispatch']=put(base/'restart-dispatch-private.json',fixtures['restart_dispatch'])
  (base/'quiesce-boot-id-private.txt').write_text(boot+'\n')
  paths['quiesce_boot_id']={'path':'quiesce-boot-id-private.txt','sha256':sha(base/'quiesce-boot-id-private.txt')}
  context['files']=paths;context['guard_sha256']=digest
  path=base/'host-context-private.json';put(path,context);return path
 path=write_context();assert o.validate_context(path,contract)==context;case('fake terminal255 dispatch accepted only as context, never boot success')
 mutations=[
  ('guard',lambda f:f['guard'].__setitem__('kernel_version','#503 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026')),
  ('guard',lambda f:f['guard'].__setitem__('soc_serial_sha256','d'*64)),
  ('guard',lambda f:f['guard']['adoption'].__setitem__('fresh_validation_sha256','d'*64)),
  ('guard',lambda f:f['guard']['stage'].__setitem__('result_sha256','d'*64)),
  ('guard',lambda f:f['guard'].__setitem__('partitions',['logdump'])),
  ('quiesce_state',lambda f:f['quiesce_state'].__setitem__('terminal',False)),
  ('quiesce_process',lambda f:f['quiesce_process'].__setitem__('status','pid_reused')),
  ('restart_dispatch',lambda f:f['restart_dispatch']['host_process'].__setitem__('terminal',False)),
  ('restart_dispatch',lambda f:f['restart_dispatch'].__setitem__('worker_sha256','d'*64)),
 ]
 original_fixtures=copy.deepcopy(fixtures)
 for name,edit in mutations:
  fixtures=copy.deepcopy(original_fixtures);edit(fixtures);path=write_context()
  reject(lambda:o.validate_context(path,contract));case('context rejects changed '+name+' '+str(len(names)))
 fixtures=copy.deepcopy(original_fixtures);path=write_context()
 context['schema']='samurai-image502-notify-fastboot-context-v1';put(path,context)
 reject(lambda:o.validate_context(path,contract));case('old prepared502 context cannot be reused')
for name,value in saved.items():setattr(o,name,value)

def functions(path):
 text=Path(path).read_text();lines=text.splitlines(True)
 return {n.name:''.join(lines[n.lineno-1:n.end_lineno]) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
baseline=REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate/fastboot-operator.py'
old,new=functions(baseline),functions(HERE/'fastboot-operator.py')
unchanged={name:hashlib.sha256(body.encode()).hexdigest() for name,body in old.items() if new.get(name)==body}
assert len(unchanged)==15
for name in ['worker','main']:
 assert new[name]==old[name].replace('samurai-image502-notify-fastboot-action-v1','samurai-usb-irq-protection-fastboot-action-v1')
result={'passed':True,'new_changed_boundary_cases':len(names),'cases':names,
 'tested_sources':{name:sha(HERE/name) for name in ['fastboot-operator.py','operator-specialization.inc','test-operator.py']},
 'unchanged_15_function_bodies':unchanged,'worker_and_main_only_action_schema_changed':True,
 'reused_old_22_case_receipt_sha256':sha(REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate/test-result.json'),
 'old_suites_rerun':False,'USB_transport_stage_auth_and_process_boundaries_fake':True,
 'runtime_request_or_guard_created':False,'device_SSH_USB_fastboot_accessed':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_changed_boundary_cases':len(names),'receipt_sha256':sha(HERE/'test-result.json')}))
