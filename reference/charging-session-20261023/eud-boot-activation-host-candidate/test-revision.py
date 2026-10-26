"""Three affected groups only; old eleven host cases are not rerun."""
from pathlib import Path
import base64,importlib.util,json,subprocess,tempfile,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eud_host_revision',HERE/'controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pins,raw=m.local_inputs(False);groups=[]
class Child:
 pid=321;returncode=0
 def __init__(self,pending=False):self.pending=pending;self.waited=0;self.communicated=False
 def communicate(self,input=None):self.communicated=True
 def wait(self,timeout=None):
  self.waited+=1
  if self.pending:raise subprocess.TimeoutExpired(['fixture'],timeout)
  return 0
with tempfile.TemporaryDirectory(prefix='eud-host-revision-') as tmp:
 root=Path(tmp);d=root/'ssh-receipt-failure';d.mkdir();program=d/'program.py';program.write_bytes(b'pass\n')
 m.save(d/'job.json',{'program':str(program),'program_sha256':m.sha(program.read_bytes()),'controller_sha256':m.sha((HERE/'controller.py').read_bytes()),'ssh_argv':['strict-original-ssh','python3 -']})
 child=Child()
 with patch.object(m,'PRIVATE',root),patch.object(m,'process_identity',side_effect=FileNotFoundError('identity race')),patch.object(m.subprocess,'Popen',return_value=child):m.ssh_worker(d/'job.json')
 assert child.communicated and child.waited==1
 assert m.load_json(d/'ssh-terminal-private.json')['receipt_error']
 try:m.terminal_job(d)
 except AssertionError:pass
 else:raise AssertionError('receipt failure qualified a reused/missing identity')
 child=Child(True)
 with patch.object(m,'ssh_argv',return_value=['strict-original-ssh','python3 -']),patch.object(m,'process_identity',side_effect=FileNotFoundError('supervisor race')),patch.object(m.subprocess,'Popen',return_value=child):
  outcome=m.start_job(root,'prepare',{'fixture':True},pins,wait_seconds=1)
 assert outcome['pending'] and child.waited==1
 assert (Path(outcome['job'])/'supervisor-receipt-error-private.json').exists()
 groups.append('Popen metadata failure still joins/waits same actual function child; no kill/replay or qualified context')

 tx='eud-boot-reconcile-fixture';d=root/tx;d.mkdir()
 fixed=json.loads((m.WORKERS/'prepare-contract.json').read_bytes())['fixed_guard_fields']
 adopted=json.loads(raw['r7_adopt_request']);board=json.loads(raw['board_receipt'])['board']
 c={'transaction_id':tx,'token':'ab'*24,'expected_boot':adopted['boot'],'fixed':fixed,
  'expected_version':adopted['version'],'expected_rootfs_sha256':adopted['rootfs'],'expected_board':board,'worker_hashes':m.WORKER_HASHES}
 m.save(d/'request-private.json',c)
 def original_job(action,value=None,rc=None,wrong_ticks=False):
  j=d/(action+'-original-job');j.mkdir();original={**c,'action':action};program=('CONFIG='+repr(original)+'\n').encode()
  m.create(j/'program.py',program);m.save(j/'job-private.json',{'action':action,'program':str(j/'program.py'),'program_sha256':m.sha(program)})
  identity={'pid':777,'startticks':100,'argv':['strict-original-ssh','python3 -']};m.save(j/'ssh-process-private.json',identity)
  if value is not None:m.create(j/'stdout-private.json',json.dumps(value).encode())
  if rc is not None:m.save(j/'ssh-terminal-private.json',{**identity,'startticks':99 if wrong_ticks else 100,'terminal':True,'returncode':rc})
  m.save(d/(action+'-job-private.json'),{'pending':True,'job':str(j),'fetch_only':True})
  return j,identity
 meta={**fixed,'transaction_id':tx,'token':c['token'],'boot_id':c['expected_boot'],'kernel_version':c['expected_version'],
  'rootfs_release_sha256':c['expected_rootfs_sha256'],'soc_serial_sha256':board['serial_sha256'],'compatible_sha256':board['compatible_sha256']}
 guard=json.dumps(meta,indent=2).encode()
 reply={'prepared':True,'transaction_id':tx,'token':c['token'],'boot_id':c['expected_boot'],'guard_sha256':m.sha(guard),'guard_base64':base64.b64encode(guard).decode()}
 job,p=original_job('prepare')
 assert m.fetch_reconcile(d)['prepare']=='original_job_pending' and not (d/'prepare-known-private.json').exists()
 m.create(job/'stdout-private.json',json.dumps(reply).encode());m.save(job/'ssh-terminal-private.json',{**p,'terminal':True,'returncode':0})
 assert m.fetch_reconcile(d)['prepare']=='original_terminal_rc0_and_bound_reply'
 assert (d/'guard-private.json').read_bytes()==guard
 c['guard_sha256']=m.sha(guard)
 base='/root/charging-management-20261023/'+tx
 q={'transaction_id':tx,'token':c['token'],'boot_id':c['expected_boot'],'pid':98,'startticks':9,
  'argv':['python3','-B',base+'/eud-quiesce.py','--guard',base+'/guard-private.json','--commit-quiesce'],
  'worker_sha256':m.WORKER_HASHES['eud-quiesce.py']}
 job,p=original_job('quiesce',{'launched':True,'process':q},0)
 assert m.fetch_reconcile(d)['quiesce']=='original_terminal_rc0_and_bound_reply'
 assert not (d/'quiesce-process-private.json').exists(),'launch ack must not fake remote child exit'
 m.save(root/'active-owner-private.json',{k:c[k] for k in ['transaction_id','token','expected_boot']})
 with patch.object(m,'local_inputs',return_value=(pins,raw)):
  try:m.run('inspect-restart',tx,True,True,private=root,start=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('must not dispatch')))
  except FileNotFoundError:pass
  else:raise AssertionError('remote quiesce PID terminal proof skipped')
 # An actual wrong terminal PID binding cannot promote or erase ownership.
 bad=root/'wrong-terminal';bad.mkdir();m.save(bad/'request-private.json',c)
 original=(job/'job-private.json').read_bytes();j2=bad/'original';j2.mkdir()
 m.create(j2/'program.py',('CONFIG='+repr({**c,'action':'prepare'})+'\n').encode())
 m.save(j2/'job-private.json',{'action':'prepare','program':str(j2/'program.py'),'program_sha256':m.sha((j2/'program.py').read_bytes())})
 m.save(j2/'ssh-process-private.json',p);m.save(j2/'ssh-terminal-private.json',{**p,'startticks':99,'terminal':True,'returncode':0});m.create(j2/'stdout-private.json',json.dumps(reply).encode())
 m.save(bad/'prepare-job-private.json',{'job':str(j2)})
 assert 'qualification_error' in m.fetch_reconcile(bad) and not (bad/'prepare-known-private.json').exists()
 assert (root/'active-owner-private.json').exists()
 groups.append('pending prepare/quiesce advance only from same hashed original stdin and exact rc0 reply; absent child alone never qualifies')

 # These raw files represent a later read-only fetch that proved the original
 # quiesce PID absent and the same token's terminal state/summary.
 m.save(d/'quiesce-process-private.json',dict(q,status='absent'))
 state={k:q[k] for k in ['transaction_id','token','boot_id','pid']};state.update(terminal=True,exit_code=0)
 m.save(d/'quiesce-state-private.json',state);m.save(d/'quiesce-summary-private.json',dict(state,taint=0))
 m.create(d/'quiesce-boot-id-private.txt',(c['expected_boot']+'\n').encode())
 argv=['python3','-B',base+'/eud-restart.py','--guard',base+'/guard-private.json','--commit-restart2-bootloader']
 m.save(d/'restart-claim-private.json',{'schema':'samurai-eud-restart-host-claim-v1','transaction_id':tx,'token':c['token'],'boot_id':c['expected_boot'],
  'guard_sha256':m.sha(guard),'request_count':1,'worker_sha256':m.WORKER_HASHES['eud-restart.py'],'argv':argv})
 job,p=original_job('restart',{},255)
 assert m.fetch_reconcile(d)['restart']=='terminal_remote_outcome_unproved'
 known=m.load_json(d/'restart-known-private.json');assert known['remote_outcome_unproved'] and known['original_ssh_returncode']==255
 context=m.export_context(d);dispatch=m.load_json(d/'restart-dispatch-private.json')
 assert dispatch['host_process']['terminal'] and dispatch['host_process']['returncode']==255 and not dispatch['syscall_success_proven'] and not dispatch['restart_claim_observed']
 path=HERE.parent/'eud-fastboot-operator/fastboot-operator.py'
 assert m.sha(path.read_bytes())=='b8f043ea4d9c904bf36bd71ec2e861f0a74e0138fadd42f2f0b34ef534430d57'
 spec=importlib.util.spec_from_file_location('frozen_ui_context_validator',path);ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
 assert ui.validate_context(d/'host-context-private.json')==context
 assert m.fetch_reconcile(d)=={},'known original result must not be replayed or rewritten'
 groups.append('original pending restart terminal255 remains unproved and exact emitted context passes frozen actual UI validator')
result={'passed':True,'new_affected_groups':groups,'reused_base_receipt_sha256':m.sha((HERE/'test-result-6682497d.json.history').read_bytes()),
 'old_11_not_rerun':True,'no_network_device_or_native_children':True,
 'files':{n:m.sha((HERE/n).read_bytes()) for n in ['controller.py','remote.py','input-pins.json','test-revision.py']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_affected_groups':len(groups),'old_11_not_rerun':True,'no_network_device_or_native_children':True}))
