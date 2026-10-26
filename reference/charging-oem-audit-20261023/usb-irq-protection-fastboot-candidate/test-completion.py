"""New saved-command completion proof only; operator/auth/USB boundaries fake."""
from pathlib import Path
import copy,hashlib,importlib.util,json,tempfile,types
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('completion_under_test',HERE/'completion-proof.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
cases=[]
def reject(call):
 try:call()
 except (ValueError,KeyError,FileNotFoundError):return
 raise AssertionError('expected rejection')
with tempfile.TemporaryDirectory() as td:
 root=Path(td);argv=['FIXTURE-FASTBOOT','-s','FIXTURE-SERIAL','reboot'];label='reboot'
 files={
  label+'-command-private.json':{'requested_argv':argv,'request_count':1},
  label+'-process-private.json':{'pid':42,'requested_argv':argv,'observed':{'pid':42,'startticks':123,'argv':['FIXTURE-ACTUAL-INTEROP']}},
  label+'-terminal-private.json':{'pid':42,'requested_argv':argv,'terminal':True,'returncode':0}}
 def write(values,out=b'OKAY',err=b''):
  (root/(label+'-stdout-private.bin')).write_bytes(out);(root/(label+'-stderr-private.bin')).write_bytes(err)
  values=copy.deepcopy(values);values[label+'-terminal-private.json'].update(
   stdout_sha256=sha(root/(label+'-stdout-private.bin')),stderr_sha256=sha(root/(label+'-stderr-private.bin')))
  for name,value in values.items():(root/name).write_text(json.dumps(value))
 write(files);assert m.saved_command(root,label,argv)==('OKAY','');cases.append('actual saved command matches original child terminal0 and raw output')
 for name,edit in [
  (label+'-command-private.json',lambda v:v.__setitem__('requested_argv',['WRONG'])),
  (label+'-process-private.json',lambda v:v['observed'].__setitem__('startticks',0)),
  (label+'-terminal-private.json',lambda v:v.__setitem__('pid',99)),
  (label+'-terminal-private.json',lambda v:v.__setitem__('terminal',False)),
  (label+'-terminal-private.json',lambda v:v.__setitem__('returncode',255))]:
  changed=copy.deepcopy(files);edit(changed[name]);write(changed)
  reject(lambda:m.saved_command(root,label,argv));cases.append('reject original command boundary '+str(len(cases)))
 write(files);(root/(label+'-stdout-private.bin')).write_bytes(b'CHANGED')
 reject(lambda:m.saved_command(root,label,argv));cases.append('changed raw output rejected')

# The completed wrapper calls real review_action with an explicit fake operator
# only for its run_action and context/auth APIs. Saved-command comparison above
# remains actual and the older 31 cases are not repeated.
with tempfile.TemporaryDirectory() as td:
 root=Path(td);context_path=root/'host-context-private.json';context_path.write_text('{}')
 context={'transaction_id':'FIXTURE','token':'a'*48,'old_boot_id':'FIXTURE-BOOT'}
 base=root/'fastboot-operator';directory=base/'flash-candidate';directory.mkdir(parents=True)
 operator=types.SimpleNamespace(IDENTITY=root/'identity.json',REBOOT_IMAGES={},local_inputs=lambda:{'fixture':True},
  read_json=lambda path:json.loads(Path(path).read_bytes()),run_action=lambda action,serial,call:{'partitions_written':['boot']})
 operator.IDENTITY.write_text(json.dumps({'serial':'FIXTURE'}))
 request={'schema':'samurai-usb-irq-protection-fastboot-action-v1','execute_authorized':True,'window_confirmed':True,
  'action':'flash-candidate','operator_sha256':sha(HERE/'fastboot-operator.py'),'inputs':{'fixture':True},
  'claimed_ns':1,'context_sha256':sha(context_path),**context}
 result={**request,'terminal':True,'passed':True,'commands_terminal':True,'partitions_written':['boot']}
 def write_action():
  (directory/'request-private.json').write_text(json.dumps(request));(directory/'result-private.json').write_text(json.dumps(result))
 write_action();review=m.review_action(operator,context_path,context,'flash-candidate')
 assert review['all_original_children_terminal0'];cases.append('action source/context/result comparison with fake dispatch boundary')
 result['commands_terminal']=False;write_action();reject(lambda:m.review_action(operator,context_path,context,'flash-candidate'))
 cases.append('unknown command completion blocks action proof')
 result['commands_terminal']=True;request['operator_sha256']='f'*64;write_action()
 reject(lambda:m.review_action(operator,context_path,context,'flash-candidate'));cases.append('changed actual operator source blocks action proof')
original_source,original_review=m.source_module,m.review_action
with tempfile.TemporaryDirectory() as td:
 root=Path(td);base=root/'fastboot-operator';base.mkdir();context_path=root/'host-context-private.json';context_path.write_text('{}')
 guard_path=root/'guard-private.json';guard_path.write_text('{}')
 context={'transaction_id':'FIXTURE','old_boot_id':'FIXTURE-BOOT','guard_sha256':sha(guard_path),'files':{'guard':{}}}
 operator=types.SimpleNamespace(validate_context=lambda path:context,prior_terminal=lambda *args:None,
  reference_file=lambda *args:guard_path,IRQ_BOOT='1'*64,LOGDUMP502='2'*64)
 m.source_module=lambda:operator
 times={'flash-candidate':1,'reboot-candidate':2}
 m.review_action=lambda operator,path,context,action:{'claimed_ns':times[action]}
 assert m.review_completed_activation(context_path)['new_boot_or_hardware_readback_verified'] is False
 cases.append('completed saved actions never assert new boot or hardware readback')
 times['reboot-candidate']=1;reject(lambda:m.review_completed_activation(context_path));times['reboot-candidate']=2
 cases.append('reboot not later than exact candidate write rejected')
 rollback=base/'rollback-original';rollback.mkdir();(rollback/'request-private.json').write_text(json.dumps({'claimed_ns':3}))
 reject(lambda:m.review_completed_activation(context_path));cases.append('later consumed rollback blocks candidate completion')
m.source_module,m.review_action=original_source,original_review
out={'passed':True,'new_cases':len(cases),'cases':cases,
 'files':{name:sha(HERE/name) for name in ['completion-proof.py','test-completion.py']},
 'operator_auth_and_USB_boundaries_fake':True,'old31_or_old22_rerun':False,
 'actual_activation_request_or_identity_created':False,'transport_or_device_accessed':False}
(HERE/'completion-test-result.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'passed':True,'new_cases':len(cases),'receipt_sha256':sha(HERE/'completion-test-result.json')}))
