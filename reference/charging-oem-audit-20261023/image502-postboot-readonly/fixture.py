"""Explicit offline fixtures only. Never produces a real new identity or guard."""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
ORIGINAL=PRIVATE/'image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json'
CONTRACT=PRIVATE/'image502-notify-materialized-001/prepare-contract.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
NEWBOOT='00000000-0000-0000-0000-000000000502'
OLDBOOT='00000000-0000-0000-0000-000000000501'

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def facts():
 r=copy.deepcopy(json.loads(ORIGINAL.read_bytes())['raw'])
 for side in ['identity_before','identity_after']:
  r[side]['boot_id']=NEWBOOT;r[side]['uname']['version']='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
 r['logdump_partition']['sha256']='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
 return r

def context_fixture(base,r):
 txn='image502-notify-live-001';token='7'*64;directory=Path(base)/txn;directory.mkdir()
 fixed=json.loads(CONTRACT.read_bytes())['fixed_guard_fields'];identity=r['identity_before']
 guard=dict(fixed,schema='samurai-image502-notify-activation-v1',transaction_id=txn,token=token,
   boot_id=OLDBOOT,kernel_version='#501 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026',
   rootfs_release_sha256=identity['rootfs']['sha256'],soc_serial_sha256=identity['serial_sha256'],
   compatible_sha256=sha(base64.b64decode(identity['compatible_b64'])))
 files={}
 def put(name,value,raw=False):
  p=directory/(name+'-private.json');p.write_text(value if raw else json.dumps(value))
  files[name]={'path':p.name,'sha256':sha(p.read_bytes())}
 put('guard',guard)
 common=dict(transaction_id=txn,token=token,boot_id=OLDBOOT)
 put('quiesce_state',dict(common,terminal=True,exit_code=0,pid=111))
 put('quiesce_summary',dict(common,taint=0));put('quiesce_boot_id',OLDBOOT+'\n',True)
 remote='/root/charging-management-20261023/'+txn
 put('quiesce_process',dict(common,pid=111,startticks=12,status='absent',argv=['python3','-B',remote+'/eud-quiesce.py','--guard',remote+'/guard-private.json','--commit-quiesce']))
 worker=json.loads((CONTRACT.parent/'activation-pins.json').read_bytes())['eud-restart.py']
 restart=dict(common,request_count=1,worker_sha256=worker,guard_sha256=files['guard']['sha256'],
  argv=['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader'])
 put('restart_claim',dict(restart,schema='samurai-eud-restart-host-claim-v1'))
 put('restart_dispatch',dict(restart,schema='samurai-eud-restart-dispatch-v1',state='dispatched_once',host_claim_sha256=files['restart_claim']['sha256'],restart_claim_intent='claimed_by_pinned_worker',host_process=dict(pid=112,startticks=13,argv=['ssh','fixture'],terminal=True,returncode=255)))
 context=dict(schema='samurai-image502-notify-fastboot-context-v1',transaction_id=txn,token=token,old_boot_id=OLDBOOT,guard_sha256=files['guard']['sha256'],files=files)
 path=directory/'host-context-private.json';path.write_text(json.dumps(context))
 return path,guard,context

def receiver_fixture(observed,request,raw,device_source):
 observed.mkdir()
 report={'schema':request['schema'],'transaction_id':request['guard']['transaction_id'],
  'context_sha256':request['context_sha256'],'guard_sha256':request['guard_sha256'],'raw':raw,'result':{'passed':True}}
 (observed/'stdout-private.json').write_text(json.dumps(report))
 (observed/'receiver-result-private.json').write_text(json.dumps({'passed':True,'transport_exit':0}))
 prefix='POSTBOOT_REQUEST=__import__("json").loads(__import__("base64").b64decode('+repr(base64.b64encode(json.dumps(request).encode()).decode())+'))\n'
 (observed/'executed-device-source.py').write_bytes(prefix.encode()+device_source)
