"""New actual launcher/journal/context boundaries only; no SSH or native calls."""
from pathlib import Path
import base64,copy,importlib.util,json,subprocess,tempfile,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eud_host',HERE/'controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pins,raw=m.local_inputs(False)
rows=[]
def passed(label):rows.append(label)
class Child:
 pid=9876
 returncode=0
 def __init__(self,pending=False):self.pending=pending;self.waited=0;self.communicated=False
 def wait(self,timeout=None):
  self.waited+=1
  if self.pending:raise subprocess.TimeoutExpired(['fixture'],timeout)
  return self.returncode
 def communicate(self,input=None):self.communicated=True;assert isinstance(input,bytes)
def identity(pid):return {'pid':pid,'startticks':111,'argv':['fixture-owned-process']}
with tempfile.TemporaryDirectory(prefix='eud-host-new-boundaries-') as temp:
 root=Path(temp)
 # Actual start_job retains the original supervisor handle on bounded timeout;
 # fake Popen has no kill/terminate API, so any blind timeout cleanup fails.
 child=Child(True)
 with patch.object(m,'ssh_argv',return_value=['strict-ssh','python3 -']),patch.object(m,'process_identity',side_effect=identity),patch.object(m.subprocess,'Popen',return_value=child):
  pending=m.start_job(root,'prepare',{'fixture':True},pins,wait_seconds=1)
 assert pending['pending'] and pending['fetch_only'] and child.waited==1
 assert (Path(pending['job'])/'supervisor-process-private.json').exists();passed('timeout retains original journal/handle without kill or replay')
 # Actual SSH supervisor records original argv/startticks then true terminal.
 job=root/'supervisor-case';job.mkdir();program=job/'program.py';program.write_bytes(b'print(1)\n')
 m.save(job/'job.json',{'controller_sha256':m.sha((HERE/'controller.py').read_bytes()),'program':str(program),'program_sha256':m.sha(program.read_bytes()),'ssh_argv':['strict-ssh','python3 -']})
 child=Child()
 with patch.object(m,'PRIVATE',root),patch.object(m,'process_identity',side_effect=identity),patch.object(m.subprocess,'Popen',return_value=child):m.ssh_worker(job/'job.json')
 term,_=m.terminal_job(job);assert child.communicated and term['terminal'] and term['returncode']==0
 try:
  with patch.object(m,'PRIVATE',root),patch.object(m.subprocess,'Popen',side_effect=AssertionError('duplicate Popen forbidden')):m.ssh_worker(job/'job.json')
 except FileExistsError:pass
 else:raise AssertionError('same original SSH job replay accepted')
 passed('SSH process true terminal retained and original job replay rejected')
 calls=[];mode={'pending':False,'fetch_terminal':False,'fetch_fail':False,'restart_rc':255}
 tx='eud-boot-controller-fixture';private=root/'transactions'
 def fake_start(directory,action,d,p,wait_seconds=35):
  calls.append(action);j=directory/('fake-'+str(len(calls)));j.mkdir()
  proc={'pid':4321,'startticks':123,'argv':['original-strict-ssh','python3 -']}
  m.save(j/'ssh-process-private.json',proc)
  if mode['pending']:return {'pending':True,'job':str(j),'fetch_only':True}
  rc=mode['restart_rc'] if action=='restart' else 255 if action=='fetch' and mode['fetch_fail'] else 0
  m.save(j/'ssh-terminal-private.json',{**proc,'terminal':True,'returncode':rc})
  guard=dict(d.get('fixed',{}),transaction_id=tx,token=d['token'],boot_id=d['expected_boot'],kernel_version=d.get('expected_version','fixture'),rootfs_release_sha256=d.get('expected_rootfs_sha256','fixture'),soc_serial_sha256='fixture',compatible_sha256='fixture')
  if action=='prepare':
   b=json.dumps(guard,indent=2).encode();value={'prepared':True,'transaction_id':tx,'token':d['token'],'guard_base64':base64.b64encode(b).decode(),'guard_sha256':m.sha(b)}
  elif action=='quiesce':value={'launched':True}
  elif action=='inspect-restart':value={'inspect_only':True,'current_boot_guard_pass':True,'quiesce_pass':True}
  elif action=='fetch':
   g=m.load_json(directory/'guard-private.json');base='/root/charging-management-20261023/'+tx
   s={'terminal':mode['fetch_terminal'],'exit_code':0,'pid':98,**{k:g[k] for k in ['transaction_id','token','boot_id']}}
   q={'status':'absent','pid':98,'startticks':9,'argv':['python3','-B',base+'/eud-quiesce.py','--guard',base+'/guard-private.json','--commit-quiesce'],**{k:g[k] for k in ['transaction_id','token','boot_id']}}
   blobs={'quiesce-state-private.json':json.dumps(s).encode(),'quiesce-summary.json':json.dumps(dict(s,taint=0)).encode(),'quiesce-boot-id-private.txt':(g['boot_id']+'\n').encode()}
   value={'same_old_boot':True,'no_cleanup_or_control_action':True,'processes':{'quiesce':q},'files':{n:{'sha256':m.sha(v),'base64':base64.b64encode(v).decode()} for n,v in blobs.items()}}
  else:value={'launched':True,'restart_outcome_unproved':True}
  (j/'stdout-private.json').write_bytes(json.dumps(value).encode());(j/'stderr-private.txt').write_bytes(b'')
  return {'pending':False,'job':str(j),'supervisor_returncode':0}
 def run(action):return m.run(action,tx,True,True,private=private,start=fake_start,require_tests=False)
 with patch.object(m,'local_inputs',return_value=(pins,raw)):
  run('prepare');directory=private/tx
  before=len(calls)
  try:run('prepare')
  except FileExistsError:pass
  else:raise AssertionError('repeated transaction accepted')
  assert len(calls)==before;passed('prepare creates a new transaction and duplicate rejects before dispatch')
  run('quiesce');run('fetch')
  assert not (directory/'quiesce-state-private.json').exists();passed('absent process plus early nonterminal snapshot does not poison stable evidence')
  mode['fetch_terminal']=True;run('fetch')
  assert m.load_json(directory/'quiesce-process-private.json')['status']=='absent'
  run('inspect-restart');run('inspect-restart');assert len(list(directory.glob('inspect-restart-known-*-private.json')))==2
  passed('terminal quiesce evidence retained and read-only inspect can be refreshed')
  outcome=run('restart');assert outcome['ssh_returncode']==255 and outcome['restart_outcome_unproved']
  context=m.load_json(directory/'host-context-private.json');assert context['schema']=='samurai-eud-fastboot-context-v1'
  assert set(context['files'])=={'guard','quiesce_state','quiesce_summary','quiesce_boot_id','quiesce_process','restart_dispatch','restart_claim'}
  dispatch=m.load_json(directory/'restart-dispatch-private.json')
  assert dispatch['host_process']['terminal'] and dispatch['host_process']['returncode']==255
  assert dispatch['host_claim_sha256']==context['files']['restart_claim']['sha256'] and not dispatch['syscall_success_proven'] and not dispatch['restart_claim_observed']
  for entry in context['files'].values():assert Path(entry['path']).name==entry['path'] and m.sha((directory/entry['path']).read_bytes())==entry['sha256']
  passed('SSH255 true terminal exports exact raw context without asserting syscall or CSR claim success')
  before=len(calls)
  try:run('restart')
  except FileExistsError:pass
  else:raise AssertionError('restart replay accepted')
  assert len(calls)==before;passed('same restart durable claim rejects second dispatch')
  mode['fetch_fail']=True;answer=run('fetch');assert answer['remote_fetch_failed'] and answer['no_cleanup_performed']
  passed('read-only fetch SSH failure preserves context and never dispatches hardware cleanup')
  oldtx=tx;tx='eud-boot-second-id-fixture';before=len(calls)
  try:run('prepare')
  except FileExistsError:pass
  else:raise AssertionError('new transaction bypassed existing activation owner')
  assert len(calls)==before;passed('a different transaction cannot bypass the original active owner')
  # New transaction prepare is pending. Only fetch is allowed; never replay
  # or advance to a quiesce after an original mutator became unknown.
  private=root/'pending-independent-fixture';tx='eud-boot-pending-fixture';mode['pending']=True;run('prepare');before=len(calls)
  try:run('quiesce')
  except FileNotFoundError:pass
  else:raise AssertionError('unknown prepare advanced to mutation')
  assert len(calls)==before;passed('pending prepare cannot advance or re-dispatch a mutator')
 # Actual remote proc classifier uses original PID/startticks and exact argv.
 remote={};exec(compile((HERE/'remote.py').read_text().split("\nif __name__=='__main__'")[0],'actual-remote-definitions','exec'),remote)
 receipt={'pid':77,'startticks':100,'argv':['python3','-B','worker']}
 class P:
  def __init__(self,*parts):self.name=str(parts[-1])
  def __truediv__(self,x):return P(x)
  def read_text(self):return '77 (fixture) S '+' '.join(['0']*18+['100'])
  def read_bytes(self):return b'python3\0-B\0worker\0'
 with patch.dict(remote,{'Path':P}):
  assert remote['proc'](receipt)['status']=='alive'
  assert remote['proc'](dict(receipt,startticks=99))['status']=='pid_reused'
 passed('actual remote proc rejects recycled PID and verifies original argv')
result={'passed':True,'cases':rows,'device_access':False,'network_or_child_executed':False,'old_suites_rerun':False,
 'files':{n:m.sha((HERE/n).read_bytes()) for n in ['controller.py','remote.py','input-pins.json','test-controller.py']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_boundaries':len(rows),'device_access':False,'network_or_child_executed':False}))
