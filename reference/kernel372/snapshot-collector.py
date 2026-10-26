"""Collect only a new owned A5 dump and the quiesced, still-owned firmware view."""
from pathlib import Path
import argparse,hashlib,json,os,re,struct,time
from dump_decoder import decode

def persist(path,data):
 with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)

def held(result):
 return bool(result.get('terminal') and result.get('phase')=='failed-held' and result.get('error') and
  result.get('cpu_release_attempted') and not result.get('cleanup_error') and
  not result.get('cpu_enabled') and not result.get('irq_enabled') and result.get('reset_asserted') and
  result.get('power_held') and result.get('backing_owned') and result.get('mapped_bytes',0)>=5*1024*1024)

def read_state(module):
 try:return json.loads((module/'parameters/result').read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}

def read_exact(fd,offset,count):
 data=bytearray()
 while len(data)<count:
  part=os.pread(fd,min(4096,count-len(data)),offset+len(data))
  if not part:raise RuntimeError('Short owned firmware view')
  data.extend(part)
 return bytes(data)

def snapshot(root,device,module,meta,expected):
 result=json.loads((module/'parameters/result').read_text())
 assert held(result) and (module/'parameters/hold_start_failure').read_text().strip() in ['Y','1']
 assert (device/'of_node').resolve(strict=True)==expected
 assert Path(meta['boot_guard']).read_bytes()==Path(meta.get('boot_id_file','/proc/sys/kernel/random/boot_id')).read_bytes()
 record=dict(attempted=True,code_page_match=False,saved=False)
 with (device/'firmware').open('rb',buffering=0) as stream:
  page=read_exact(stream.fileno(),0,4096)
  record['code_page_sha256']=hashlib.sha256(page).hexdigest()
  persist(root/'firmware-code-private.bin',page)
  if record['code_page_sha256']!=meta['firmware_code_page_sha256']:
   record['reason']='owned code page differs from retained ELF; exception state not read';return record
  record['code_page_match']=True
  # Fixed offsets belong to this verified OEM ELF, not the reusable SoC driver.
  assert meta['firmware_sha256']=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
  exception=read_exact(stream.fileno(),0x109000,4096)
  l1=read_exact(stream.fileno(),0x340000,16384)
  assert held(json.loads((module/'parameters/result').read_text()))
  persist(root/'firmware-exception-private.bin',exception)
  persist(root/'firmware-l1-private.bin',l1)
  far,fsr,typ=struct.unpack_from('<3I',exception,0x9a0)
  addresses=[0,0x1099a0,0x07400000,0x0741c000,0x10a00000,0xe001004c,far]
  tables={}
  for address in addresses:
   pte=struct.unpack_from('<I',l1,(address>>20)*4)[0]
   if (pte&3)!=1:continue
   offset=pte&0xfffffc00
   if offset in tables:continue
   if not (0x344000<=offset and offset+1024<=0x384000):
    record.setdefault('invalid_l2_offsets',[]).append(offset);continue
   data=read_exact(stream.fileno(),offset,1024);name='firmware-l2-'+format(offset,'x')+'-private.bin'
   persist(root/name,data);tables[offset]=name
  assert held(json.loads((module/'parameters/result').read_text()))
  decoded=dict(far=far,fsr=fsr,exception_type=typ,l2_tables=tables,
   no_claim_of_a5_dirty_cache_visibility=True)
  persist(root/'firmware-exception-decoded-private.json',json.dumps(decoded,indent=2).encode())
  record.update(saved=True,exception_fields_nonzero=bool(far or fsr or typ),l2_tables=len(tables))
 return record

def collect(root,sysfs,dt_base,module,devices,seconds=10):
 os.umask(0o077);meta=json.loads((root/'manifest.json').read_text());start=time.monotonic()
 expected=dt_base/'soc@0/samurai-icp356-boot@ac10000';device=devices/'ac10000.samurai-icp356-boot'
 baseline={p.name for p in sysfs.glob('devcd*')}
 pending=None
 result=dict(pid=os.getpid(),terminal=False,captured=False,owned_snapshot_acknowledged=False,snapshot_attempted=False,snapshot_saved=False)
 persist(root/'collector-ready.json',json.dumps(dict(pid=os.getpid(),ready=True,baseline_names=sorted(baseline))).encode())
 try:
  while time.monotonic()-start<seconds and not (root/'collector-stop').exists():
   if not result['snapshot_attempted'] and (module/'parameters/result').exists() and (device/'firmware').exists():
    state=read_state(module)
    if held(state):
     result['snapshot_attempted']=True
     snap=snapshot(root,device,module,meta,expected);result['snapshot']=snap;result['snapshot_saved']=snap['saved']
     persist(root/'snapshot-result-private.json',json.dumps(snap,indent=2).encode())
   if not result['captured']:
    for candidate in sysfs.glob('devcd*'):
     if candidate.name in baseline or not re.fullmatch(r'devcd\d+',candidate.name):continue
     try:
      failing=(candidate/'failing_device').resolve(strict=True)
      if failing.name!=device.name or (failing/'of_node').resolve(strict=True)!=expected:continue
      with (candidate/'data').open('rb') as stream:raw=stream.read(569)
     except FileNotFoundError:continue
     persist(root/('a5-'+candidate.name+'-private.bin'),raw)
     result.update(captured=True,name=candidate.name,bytes=len(raw))
     decoded=decode(raw);persist(root/'a5-dump-decoded-private.json',json.dumps(decoded,indent=2).encode())
     result.update(decoded=True,init_response=decoded['init_response'],sfr_characters=len(decoded['sfr']))
     pending=candidate
     break
   if result['captured'] and result['snapshot_attempted']:break
   time.sleep(.002)
  result['timeout']=time.monotonic()-start>=seconds and not (root/'collector-stop').exists()
  if pending is not None:
   # Keep the standard failing-device reference until the firmware window
   # was examined (or a bounded wait ended); all files already fsync'd.
   if pending.exists():
    failing=(pending/'failing_device').resolve(strict=True)
    assert failing.name==device.name and (failing/'of_node').resolve(strict=True)==expected
    with (pending/'data').open('wb') as stream:stream.write(b'1')
   deadline=time.monotonic()+2
   while pending.exists() and time.monotonic()<deadline:time.sleep(.002)
   result['owned_snapshot_acknowledged']=not pending.exists()
   if not result['owned_snapshot_acknowledged']:raise RuntimeError('Owned devcoredump still retains device reference')
  return result
 except BaseException as error:
  result['error']=str(error);return result
 finally:
  result.update(terminal=True,seconds=round(time.monotonic()-start,3))
  persist(root/'collector-result.json',json.dumps(result,indent=2).encode())

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
 parser.add_argument('--sysfs',type=Path,default=Path('/sys/class/devcoredump'))
 parser.add_argument('--dt-base',type=Path,default=Path('/sys/firmware/devicetree/base'))
 parser.add_argument('--module',type=Path,default=Path('/sys/module/camss_icp_a5_boot_test'))
 parser.add_argument('--devices',type=Path,default=Path('/sys/bus/platform/devices'))
 parser.add_argument('--seconds',type=float,default=10)
 args=parser.parse_args();collect(args.root,args.sysfs,args.dt_base,args.module,args.devices,args.seconds)
