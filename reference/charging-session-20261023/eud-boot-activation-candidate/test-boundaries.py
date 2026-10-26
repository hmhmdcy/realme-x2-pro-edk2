"""Only changed guard/whole-word CSR/claim boundaries; fake OS, no transport."""
from pathlib import Path,PurePosixPath
import ast,copy,ctypes,hashlib,io,json,struct,types
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=(HERE/'eud-restart.py').read_text()
fragment=(HERE/'guard-fragment.py').read_text().split('\nassert len(sys.argv)==4')[0]
env={'Path':Path,'os':types.SimpleNamespace(),'json':json}
exec(compile(fragment,'actual-guard-fragment','exec'),env)
wrapper=(PRIVATE/'kernel481/formal-expected-private.json').read_bytes()
manifest=(PRIVATE/'charging-management-20261023/r8-candidate/manifest.json').read_bytes()
assert sha(wrapper)==env['CAMERA481'] and sha(manifest)==env['R8_MANIFEST']
txn='eud-boot-new-fixture';guard='/root/charging-management-20261023/'+txn+'/guard-private.json'
uname=types.SimpleNamespace(machine='aarch64',release='7.3.0-rc6-rmx1931-samurai-k363+',version='#363 exact-fixture')
boot='11111111-2222-3333-4444-555555555555'
meta=dict(schema=env['EUD_BOOT_SCHEMA'],transaction_id=txn,token='7a'*16,boot_id=boot,
 old_boot_guard_path=env['OLD_BOOT_GUARD'],kernel_release=uname.release,kernel_version=uname.version,
 rootfs_release_sha256=sha(b'ROOTFS_ID=samurai-f2fs-rootfs01\n'),soc_serial_sha256=sha(b'fixture-soc'),
 compatible_sha256=sha(b'realme,samurai\0qcom,sm8150\0'),candidate_boot_sha256=env['CANDIDATE_BOOT'],
 rollback_boot_sha256=env['ROLLBACK_BOOT'],partition='boot',boot_bytes=100663296,
 image363_sha256=env['IMAGE363'],logdump_sha256=env['LOGDUMP365'],camera481_expected_sha256=env['CAMERA481'],
 camera_return_proof_sha256=env['CAMERA_RETURN'],charging_manifest_sha256=env['R8_MANIFEST'])
files={};digest_fixtures={};stats={};blocks={};block_reads=[]
def put(p,raw,digest=None):
 files[p]=raw
 if digest:digest_fixtures[raw]=digest
put('/etc/samurai-rootfs-release',b'ROOTFS_ID=samurai-f2fs-rootfs01\n')
put('/proc/sys/kernel/random/boot_id',(boot+'\n').encode());put(env['OLD_BOOT_GUARD'],(boot+'\n').encode())
put('/proc/sys/kernel/tainted',b'0\n');put('/sys/devices/soc0/serial_number',b'fixture-soc')
put('/sys/firmware/devicetree/base/compatible',b'realme,samurai\0qcom,sm8150\0')
put('/usr/share/samurai-charging/manifest.json',manifest)
put(str(PurePosixPath(guard).parent/'camera481-expected-private.json'),wrapper)
for p,digest in {**json.loads(manifest)['installed_files'],**json.loads(wrapper)['expected']['installed_files']}.items():
 put(p,('fixture-content:'+p).encode(),digest)
notes={**env['R8_NOTES'],**{n:i['note'] for n,i in json.loads(wrapper)['expected']['modules'].items()},'s5k3m5':env['SENSOR468_NOTE']}
for n,digest in notes.items():
 put('/sys/module/'+n+'/notes/.note.gnu.build-id',('note:'+n).encode(),digest)
 put('/sys/module/'+n+'/initstate',b'live\n')
put('/sys/module/samurai_usb_input/parameters/native_retained',b'Y\n')
put('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower',b'100\n')
put('/lib/apk/db/installed','\n\n'.join('P:'+p+'\nV:'+v for p,v in json.loads(wrapper)['expected']['packages'].items()).encode())
sample=dict(valid=1,online=1,protection_ok=1,age_ms=900,shadow=0,error=0,stop_error=0,latched=0,fault=0,source_inhibit=0,thermal_inhibit=0,cycle_timeout=0,gauge_charge_stop=0,flags=192,session_seconds=1200,desired_enable=1)
telemetry='/sys/bus/i2c/devices/0-005c/telemetry'
def sample_put(**change):
 value={**sample,**change};put(telemetry,' '.join(k+'='+str(v) for k,v in value.items()).encode())
sample_put()
blocks.update({'/dev/disk/by-partlabel/boot':(100663296,env['ROLLBACK_BOOT']),'/dev/disk/by-partlabel/logdump':(67108864,env['LOGDUMP365'])})
class FakePath:
 def __init__(self,*parts):self.p=PurePosixPath(*(str(x) for x in parts))
 def __str__(self):return str(self.p)
 def __eq__(self,other):return str(self)==str(other)
 def __truediv__(self,x):return FakePath(self.p/x)
 @property
 def parent(self):return FakePath(self.p.parent)
 @property
 def name(self):return self.p.name
 def is_file(self):return str(self) in files
 def is_symlink(self):return stats.get(str(self),{}).get('symlink',False)
 def is_absolute(self):return self.p.is_absolute()
 def exists(self):return str(self) in files
 def stat(self):return types.SimpleNamespace(st_uid=stats.get(str(self),{}).get('uid',0),st_mode=stats.get(str(self),{}).get('mode',0o100600))
 def read_bytes(self):return files[str(self)]
 def read_text(self):return self.read_bytes().decode()
def fixture_hash(raw):return types.SimpleNamespace(hexdigest=lambda:digest_fixtures.get(raw,sha(raw)))
def block_boundary(p,n):
 block_reads.append((p,n));actual,digest=blocks[p];assert actual==n;return digest
env.update(Path=FakePath,os=types.SimpleNamespace(uname=lambda:uname),hashlib=types.SimpleNamespace(sha256=fixture_hash),block_sha=block_boundary)
rows=[]
def guard_case(label,change=None,edit=None,accepted=False):
 saved=(copy.deepcopy(files),copy.deepcopy(stats),copy.deepcopy(blocks));m=copy.deepcopy(meta)
 try:
  if change:change(m)
  if edit:edit()
  put(guard,json.dumps(m).encode())
  try:env['validate_activation_guard'](FakePath(guard))
  except (AssertionError,KeyError):assert not accepted,label
  else:assert accepted,label
  rows.append({'label':label,'accepted':accepted})
 finally:
  for target,old in zip((files,stats,blocks),saved):target.clear();target.update(old)
guard_case('current R8 and formal481, a30 boot',accepted=True)
guard_case('safe controlled INHIBIT is allowed before restart',edit=lambda:sample_put(desired_enable=0),accepted=True)
guard_case('old R7 schema rejected',lambda m:m.update(schema='samurai-r7-restart-review-v1'))
guard_case('old transaction rejected',lambda m:m.update(transaction_id='charging-r7-used-fixture'))
guard_case('bad token rejected',lambda m:m.update(token='old'))
guard_case('wrong old boot rejected',lambda m:m.update(boot_id='old'))
guard_case('SoC mismatch rejected',lambda m:m.update(soc_serial_sha256='0'*64))
guard_case('candidate mismatch rejected',lambda m:m.update(candidate_boot_sha256='0'*64))
guard_case('wrong partition rejected',lambda m:m.update(partition='logdump'))
guard_case('actual boot mismatch rejected',edit=lambda:blocks.update({'/dev/disk/by-partlabel/boot':(100663296,'0'*64)}))
guard_case('actual logdump mismatch rejected',edit=lambda:blocks.update({'/dev/disk/by-partlabel/logdump':(67108864,'0'*64)}))
guard_case('old R6 loaded note rejected',edit=lambda:put('/sys/module/samurai_usb_input/notes/.note.gnu.build-id',b'old-R6-note'))
guard_case('old camera library rejected',edit=lambda:put('/usr/lib/libcamera.so.0.7.2',b'old-camera-library'))
guard_case('468 sensor note mismatch rejected',edit=lambda:put('/sys/module/s5k3m5/notes/.note.gnu.build-id',b'old-sensor'))
guard_case('old440 wrapper rejected',edit=lambda:put(str(PurePosixPath(guard).parent/'camera481-expected-private.json'),b'old440'))
guard_case('old timeout rejected',edit=lambda:sample_put(cycle_timeout=1))
guard_case('stale sample rejected',edit=lambda:sample_put(age_ms=3001))
guard_case('prior claim rejects repeated restart before mutation',edit=lambda:put('/run/'+txn+'-reboot-phase-private.json',b'claimed'))

# Same emitted guard text in both complete workers. Ordinary hardware quiesce
# suffix remains byte-for-byte after only work/receipt metadata normalization.
for name in ('eud-quiesce.py','eud-restart.py'):
 text=(HERE/name).read_text();ast.parse(text);assert (HERE/'guard-fragment.py').read_text() in text
old=(HERE.parents[1]/'charging-oem-audit-20261023/normal-restart-candidate/r7-quiesce-review.py').read_text()
new=(HERE/'eud-quiesce.py').read_text()
marker="assert sys.argv[3]=='--commit-quiesce'"
normalized=new[new.index(marker):].replace("work='eud-boot-activation'","work='charging-r7-restart'").replace(",token=meta['token']",'')
assert normalized==old[old.index(marker):]

# The actual new restart try body; only OS/MMIO/native syscall boundaries fake.
class Transferred(BaseException):pass
tail=next(n for n in ast.parse(source).body if isinstance(n,ast.Try))
tail_code=compile(ast.Module(body=[tail],type_ignores=[]),'actual-eud-restart-tail','exec')
def tail_case(label,value,readback=None,claimed=False,fsync_error=False):
 image=bytearray(4096);struct.pack_into('<I',image,0x14,value)
 events=[];s={'unbound':False,'calls':0,'thaws':0};claims=[]
 class File(io.StringIO):
  def fileno(self):return 900
  def __exit__(self,*args):claims.append(json.loads(self.getvalue()));return False
 class Phase:
  parent='/run'
  def open(self,mode):
   assert mode=='x';events.append('claim')
   if claimed:raise FileExistsError()
   return File()
  def write_text(self,text):events.append('phase')
 class Mapping:
  def __enter__(self):return image
  def __exit__(self,*args):events.append('mapping-close')
 class Driver:
  def exists(self):return not s['unbound']
 class Device:
  name='88e0000.serial'
  def __truediv__(self,k):assert k=='driver';return Driver()
 class BoundaryPath:
  def __init__(self,p):assert p=='/sys/bus/platform/drivers/qcom_eud_com/unbind'
  def write_text(self,x):assert x=='88e0000.serial';s['unbound']=True;events.append('unbind')
 def fsync(fd):
  events.append('fsync')
  if fsync_error:raise OSError('claim fsync fixture')
 def ioctl(fd,op,x):
  if op==0xc0045877:events.append('freeze')
  else:assert op==0xc0045878;s['thaws']+=1
 def syscall(*args):
  assert args[0]==142 and args[3]==0xa1b2c3d4;s['calls']+=1;events.append('syscall142');raise Transferred()
 def pack(fmt,buf,off,x):struct.pack_into(fmt,buf,off,x if readback is None else readback)
 g=dict(fd=101,rootfd=None,frozen=False,phase=Phase(),device=Device(),meta=meta,Path=BoundaryPath,
  mmap=types.SimpleNamespace(mmap=lambda *a,**kw:Mapping(),MAP_SHARED=1,PROT_READ=1,PROT_WRITE=2),
  os=types.SimpleNamespace(open=lambda *a:202,O_RDONLY=0,O_DIRECTORY=1,fsync=fsync,sync=lambda:events.append('sync'),close=lambda fd:events.append('close')),
  sys=types.SimpleNamespace(argv=['worker','--guard',guard,'--commit-restart2-bootloader']),fcntl=types.SimpleNamespace(ioctl=ioctl),
  struct=types.SimpleNamespace(unpack_from=struct.unpack_from,pack_into=pack),json=json,print=lambda *a,**kw:events.append('print'),
  time=types.SimpleNamespace(sleep=lambda x:events.append('sleep')),ctypes=ctypes,
  libc=types.SimpleNamespace(syscall=syscall),command=ctypes.create_string_buffer(b'bootloader\0'))
 try:exec(tail_code,g)
 except Transferred:s['outcome']='transferred'
 except Exception as e:s['outcome']=type(e).__name__
 accepted=value in (0,1,0x01010101) and readback in (None,0) and not claimed and not fsync_error
 assert s['calls']==int(accepted),(label,s,events)
 if value not in (0,1,0x01010101) or claimed or fsync_error:assert not s['unbound']
 if accepted:
  assert struct.unpack_from('<I',image,0x14)[0]==0
  assert claims[0]['token']==meta['token'] and claims[0]['request_count']==1
  assert events[events.index('unbind')+1:events.index('syscall142')]==[]
  assert events.index('fsync')<events.index('freeze')
 return {'label':label,'calls':s['calls'],'unbound':s['unbound'],'outcome':s['outcome']}
tails=[tail_case('whole 0 accepted',0),tail_case('whole 1 accepted',1),tail_case('actual replicated word accepted',0x01010101),
 tail_case('unknown low-byte-1 word rejected',0x00000101),tail_case('whole nonzero low-byte0 readback rejected',1,0x01000000),
 tail_case('existing claim prevents repeat mutation',1,claimed=True),tail_case('claim fsync failure blocks mutation',1,fsync_error=True)]
assert source.index("if sys.argv[3]=='--inspect'")<source.index("os.open('/dev/mem'")
result={'passed':True,'actual_guard_cases':rows,'actual_restart_tail_cases':tails,'unchanged_quiesce_hardware_suffix':True,
 'guard_crypto_OS_boundaries':'fake finite files/digests and block IO; no claim of SHA algorithm testing',
 'reused_old_hardware_guard_cases':17,'reused_old_transport_tail_cases':8,'old_suites_rerun':False,
 'device_access':False,'native_syscall_executed':False,'files':{n:sha((HERE/n).read_bytes()) for n in ['guard-fragment.py','eud-quiesce.py','eud-restart.py','test-boundaries.py']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'guard_cases':len(rows),'actual_tail_cases':len(tails),'hardware_quiesce_suffix_unchanged':True,'device_access':False}))
