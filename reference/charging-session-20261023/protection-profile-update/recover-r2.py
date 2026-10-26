"""Restore the known partial three-file stage, then resume the unchanged driver."""
from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('profile_recover_adapter',Path(__file__).resolve().parent/'host.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a);u=a.u
# Historical once-only transaction, already recovered. Later adapters must
# never redirect this recovery to their current transaction.
u.OUT=u.BASE/'protection-profile-update-live-20261024-02'
u.TX='irq-native-usb-pm-stage-protocol-20261024-02'
u.REMOTE='/root/charging-management-20261023/'+u.TX
request=u.request();rows=list(u.OUT.glob('raw-*/device-stage/result.json'));assert len(rows)==1
raw=rows[0].read_bytes();result=json.loads(raw);terminal=json.loads((rows[0].parent.parent/'worker-terminal-private.json').read_bytes())
assert terminal['terminal'] and terminal['returncode']==1 and result['terminal'] and result['disk_state']=='partial_known' and result['stop_verified']
c=json.loads((a.HERE/'cohort-r2-result.json').read_bytes())
packet=dict(root=u.REMOTE,request=request,result_sha256=u.sha(raw),new_service_sha256=c['target_service_sha256'],old_files=c['source_files'],new_files=c['target_files'])
code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import hashlib,json,os,runpy
root=Path(PACKET['root']);request=PACKET['request'];oldout=root/'device-stage'
assert hashlib.sha256((root/'stage-worker.py').read_bytes()).hexdigest()==request['worker_sha256']
assert hashlib.sha256((oldout/'result.json').read_bytes()).hexdigest()==PACKET['result_sha256']
terminal=json.loads((root/'worker-terminal-private.json').read_bytes());assert terminal['terminal'] and terminal['returncode']==1
assert terminal['process']==json.loads((root/'worker-process-private.json').read_bytes())
source=runpy.run_path(str(root/'stage-worker.py'),run_name='recovery_source_only')
dev=source['Device']((json.dumps(request,indent=2)+'\n').encode());dev.request=request
recovery=root/'partial-recovery-r2';assert not recovery.exists();os.umask(0o077);recovery.mkdir(mode=0o700)
events=[];reply=dict(passed=False,old_disk_restored=False,old_runtime_resumed=False,new_query_started=False,source_transaction_not_replayed=True)
def save(name,value):
 with (recovery/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def event(value):
 events.append(value)
 with (recovery/'events.jsonl').open('a') as f:f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
try:
 dev.identity(request);dev.lock_existing(False);dev.board_client();dev.open_mac()
 stopped=json.loads((oldout/'stopped-private.json').read_bytes())
 assert dev.mac_evidence()==stopped['mac_evidence']
 for name in source['NOTES']:
  assert dev.module_state(name)=='live'
  assert hashlib.sha256(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()).hexdigest()==source['NOTES'][name]
 service=source['SERVICE'];target=source['USB'];manifest=source['MANIFEST']
 assert {name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source['ORDER']}=={
  target:PACKET['new_files'][target],service:PACKET['new_files'][service],manifest:PACKET['old_files'][manifest]}
 manager=dev.manager(PACKET['new_service_sha256']);before=dev.observe(manager)
 source['safe_sample'](before);source['source_limits'](before)
 assert before['registers']['08']&0x18==8 and before['sample']['desired_enable']==0 and before['sample']['hold_requested']==before['sample']['full_holding']==0
 save('before.json',before)
 # Restore executable manager first, so the original manager guard becomes
 # valid again before any subsequent state observation or AUTO request.
 for name in [service,target,manifest]:
  backup=oldout/(Path(name).name+'.before');old=backup.read_bytes();assert hashlib.sha256(old).hexdigest()==PACKET['old_files'][name]
  current=Path(name).read_bytes();digest=hashlib.sha256(current).hexdigest();assert digest in [PACKET['old_files'][name],PACKET['new_files'][name]]
  if current!=old:source['atomic_replace'](name,old,request['transaction_id']+'-recovery-r2',digest,event)
 assert {name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source['ORDER']}==PACKET['old_files']
 reply['old_disk_restored']=True
 manager=dev.manager(source['SERVICE_SHA']);meta=dev.verify(manager);dev.notes_match(manager,meta)
 still=dev.observe(manager);source['safe_sample'](still);assert still['registers']['08']&0x18==8
 resume=manager['command'](meta,'resume');assert resume['managed'] is True
 after=dev.observe(manager);mode=source['healthy'](after,True);source['unchanged'](before,after)
 assert after['mac_evidence']==stopped['mac_evidence'] and after['notes']==source['NOTES']
 save('after.json',after);reply.update(passed=True,old_runtime_resumed=True,healthy_mode=mode,notes=after['notes'],manifest_sha256=source['OLD'])
except BaseException as error:
 reply['error']=repr(error)
 if reply['old_disk_restored']:
  try:
   manager=dev.manager(source['SERVICE_SHA']);manager['inhibit'](manager['live'].PSY/'mp2650-input');reply['failure_inhibit_verified']=dev.registers()['08']&0x18==8
  except BaseException as secondary:reply['inhibit_error']=repr(secondary)
finally:
 dev.close();save('result.json',reply)
print(json.dumps(reply))
assert reply['passed'],reply
'''
print(json.dumps(u.call('partial-recovery-r2',code,False),indent=2))
