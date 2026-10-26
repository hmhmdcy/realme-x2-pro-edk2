"""Only Image501 migration boundaries; actual functions with fake OS/transport."""
from pathlib import Path,PurePosixPath
import ast,copy,ctypes,fnmatch,hashlib,importlib.util,io,json,tempfile,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'eud-boot-activation-candidate'
HOST=HERE.parent/'eud-boot-activation-host-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('image501_host',HERE/'controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pins,raw=m.local_inputs(False);groups=[]

# Reuse the finite file/crypto fixture setup, not any old test cases/algorithms.
setup=(OLD/'test-boundaries.py').read_text().split("guard_case('current R8",1)[0]
setup=setup.replace("HERE=Path(__file__).resolve().parent",'HERE=NEW_HERE')
setup=setup.replace("txn='eud-boot-new-fixture'", "txn='image501-new-fixture'")
g={'__file__':str(HERE/'test-delta.py'),'NEW_HERE':HERE};exec(compile(setup,'old-finite-fixture-setup-only','exec'),g)
fixed=json.loads((HERE/'prepare-contract.json').read_bytes())['fixed_guard_fields'];g['meta'].update(fixed)
for k in ['partition','logdump_sha256','camera_return_proof_sha256']:g['meta'].pop(k,None)
put,env,files=g['put'],g['env'],g['files']
put('/usr/local/sbin/samurai-usb',b'fixture-startup500',env['STARTUP500'])
put('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower',b'500\n')
put('/sys/firmware/devicetree/base/soc@0/serial@88e0000/compatible',b'qcom,sm8150-eud-com\0')
put('/sys/firmware/devicetree/base/soc@0/serial@88e0000/status',b'disabled\0')
put('/proc/consoles',b'tty0 -WU (EC p a) 4:7\n');put('/proc/cmdline',b'console=tty0 loglevel=7')
g['FakePath'].glob=lambda self,pattern:[g['FakePath'](p) for p in files if str(PurePosixPath(p).parent)==str(self) and fnmatch.fnmatch(PurePosixPath(p).name,pattern)]
case=g['guard_case']
case('current4126/ACA/R8/startup500 pair profile',accepted=True)
case('candidate logdump must match',lambda v:v.update(candidate_logdump_sha256='0'*64))
case('rollback logdump must match',lambda v:v.update(rollback_logdump_sha256='0'*64))
case('old eud transaction rejected',lambda v:v.update(transaction_id='eud-boot-old-fixture'))
case('startup100 bytes rejected',edit=lambda:put('/usr/local/sbin/samurai-usb',b'old100'))
case('MaxPower100 rejected',edit=lambda:put('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower',b'100'))
case('enabled COM rejected without hardware IO',edit=lambda:put('/sys/firmware/devicetree/base/soc@0/serial@88e0000/status',b'okay\0'))
case('bound COM rejected without controls',edit=lambda:put('/sys/bus/platform/devices/88e0000.serial/driver',b'driver'))
case('live EUD tty rejected',edit=lambda:put('/sys/class/tty/ttyEUD0',b'tty'))
case('live eud console rejected',edit=lambda:put('/proc/consoles',b'ttyEUD0 -WU'))
groups.append({'group':'actual new guard','cases':g['rows']})

# Exact quiesce hardware suffix, and unchanged supervisor/once/unknown methods.
marker="assert sys.argv[3]=='--commit-quiesce'"
old=(OLD/'eud-quiesce.py').read_text();new=(HERE/'eud-quiesce.py').read_text()
assert new[new.index(marker):].replace("work='image501-activation'","work='eud-boot-activation'")==old[old.index(marker):]
def function_map(path):return {n.name:n for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a,b=function_map(HOST/'controller.py'),function_map(HERE/'controller.py')
same=['create','save','process_identity','process_status','ssh_worker','start_job','terminal_job','require_known','reconcile','fetch_reconcile','retain_fetch','copy_exact','host_jobs']
for n in same:assert ast.dump(a[n])==ast.dump(b[n]),n
source=(HERE/'remote.py').read_text().replace('/run/samurai-image501-activation-owner-private.json','/run/samurai-eud-boot-activation-owner-private.json').replace("r'image501-[a-z0-9-]{8,64}'","r'eud-boot-[a-z0-9-]{8,64}'")
assert source==(HOST/'remote.py').read_text()
groups.append({'group':'unchanged quiesce and supervisor/once/unknown flow','same_functions':same,'remote_delta_only_owner_and_tx_regex':True})

# Actual new restart try body: no obsolete EUD MMIO/driver path remains.
source=(HERE/'eud-restart.py').read_text();tree=ast.parse(source)
assert not any(word in source for word in ['/dev/mem','mmap','pack_into','/unbind','0x088e1000'])
tail=next(n for n in tree.body if isinstance(n,ast.Try));code=compile(ast.Module(body=[tail],type_ignores=[]),'actual-image501-restart-tail','exec')
class Transferred(BaseException):pass
tail_rows=[]
def tail_case(label,mode='transfer'):
 events=[];claims=[];calls=0
 class File(io.StringIO):
  def fileno(self):return 900
  def __exit__(self,*args):claims.append(self.getvalue());return False
 class Phase:
  parent='/run'
  def open(self,kind):
   assert kind=='x';events.append('claim')
   if mode=='claimed':raise FileExistsError()
   return File()
  def write_text(self,x):
   events.append('phase')
   if mode=='logfail':raise BrokenPipeError()
 def fsync(fd):
  events.append('fsync')
  if mode=='fsyncfail':raise OSError('fixture fsync')
 def ioctl(fd,op,arg):
  assert fd==202 and arg==0
  if op==0xc0045877:
   events.append('freeze')
   if mode=='freezefail':raise OSError('fixture freeze')
  else:assert op==0xc0045878;events.append('thaw')
 def syscall(*args):
  nonlocal calls
  calls+=1;assert args[0:4]==(142,0xfee1dead,672274793,0xa1b2c3d4);events.append('syscall')
  if mode=='return':return -1
  if mode=='syscallerr':raise OSError('fixture syscall')
  raise Transferred()
 ns=dict(os=types.SimpleNamespace(open=lambda *a:202,O_RDONLY=0,O_DIRECTORY=1,fsync=fsync,sync=lambda:events.append('sync'),close=lambda fd:events.append('close')),
  sys=types.SimpleNamespace(argv=['worker','--guard','guard','--commit-restart2-bootloader']),phase=Phase(),meta=g['meta'],
  rootfd=None,frozen=False,fcntl=types.SimpleNamespace(ioctl=ioctl),json=json,ctypes=ctypes,
  libc=types.SimpleNamespace(syscall=syscall),command=ctypes.create_string_buffer(b'bootloader\0'),
  print=lambda *a,**kw:events.append('print'))
 try:exec(code,ns)
 except Transferred:outcome='transferred'
 except Exception as e:outcome=type(e).__name__
 else:raise AssertionError('tail unexpectedly returned')
 expected=mode in ['transfer','logfail','return','syscallerr'];assert calls==int(expected)
 assert events.count('freeze')==int(mode not in ['claimed','fsyncfail'])
 assert events.count('thaw')==int(mode in ['return','syscallerr'])
 assert events[-1]=='close'
 if calls:assert events.index('claim')<events.index('fsync')<events.index('freeze')<events.index('syscall')
 tail_rows.append({'label':label,'calls':calls,'outcome':outcome,'events':events})
for label,mode in [('single RESTART2','transfer'),('log failure still single syscall','logfail'),('existing claim blocks','claimed'),('claim fsync failure blocks','fsyncfail'),('freeze error closes without syscall','freezefail'),('returned syscall thaws and closes','return'),('raised syscall thaws and closes','syscallerr')]:tail_case(label,mode)
groups.append({'group':'actual EUD-off restart tail','cases':tail_rows,'no_MMIO_or_EUD_control':True})

# Actual migrated prepare builds its fresh identity from R3, not old camera boot.
with tempfile.TemporaryDirectory(prefix='image501-activation-delta-') as tmp:
 private=Path(tmp);tx='image501-boundary-fixture';seen=[]
 def pending(directory,action,data,p):
  seen.append((action,data));assert action=='prepare'
  current=m.profile(raw);assert data['expected_boot']==current['identity']['boot_id']
  assert data['expected_version']==current['identity']['uname']['version']
  assert data['fixed']==fixed
  return {'pending':True,'job':str(directory/'original-job'),'fetch_only':True}
 result=m.run('prepare',tx,True,True,private=private,start=pending,require_tests=False)
 assert result['pending'] and len(seen)==1
 assert (private/tx/'prepare-intent-private.json').exists() and (private/'active-owner-private.json').exists()
 try:m.run('prepare',tx,True,True,private=private,start=pending,require_tests=False)
 except FileExistsError:pass
 else:raise AssertionError('second prepare dispatched')
 assert len(seen)==1
 try:m.run('prepare','eud-boot-used-fixture',True,True,private=private,start=pending,require_tests=False)
 except AssertionError:pass
 else:raise AssertionError('old transaction accepted')
 bad=dict(raw);adopt=json.loads(raw['adoption']);adopt['guard_path']='old-guard';bad['adoption']=json.dumps(adopt).encode()
 try:m.profile(bad)
 except AssertionError:pass
 else:raise AssertionError('old adopted guard accepted')
groups.append({'group':'actual migrated host prepare','one_pending_dispatch_and_durable_claim':True,'second_or_old_tx_rejected':True,'wrong_adoption_rejected':True})

result={'passed':True,'groups':groups,'native_worker_or_syscall_or_transport_executed':False,'old_suites_rerun':False,
 'reused_old_worker_receipt_sha256':sha((OLD/'test-result.json').read_bytes()),'reused_old_host_receipt_sha256':sha((HOST/'test-result.json').read_bytes()),
 'files':{n:sha((HERE/n).read_bytes()) for n in ['controller.py','remote.py','input-pins.json','prepare-contract.json','guard-fragment.py','eud-quiesce.py','eud-restart.py','test-delta.py']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'groups':len(groups),'new_guard_cases':len(g['rows']),'new_tail_cases':len(tail_rows),'no_transport_device_or_native_worker':True}))
