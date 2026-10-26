"""Observe standard devcoredump for the normal, statically described ICP only."""
from pathlib import Path
import hashlib,json,os,sys,time,traceback
root=Path(sys.argv[1]);device=Path('/sys/bus/platform/devices/ac10000.icp').resolve();node=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000').resolve();sysfs=Path('/sys/class/devcoredump')
def persist(path,data):
 with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
baseline={p.name for p in sysfs.glob('devcd*')};result=dict(pid=os.getpid(),terminal=False,captured=False,acknowledged=False)
persist(root/'collector-ready.json',json.dumps(dict(pid=os.getpid(),ready=True)).encode());start=time.monotonic()
try:
 while time.monotonic()-start<600 and not (root/'collector-stop').exists():
  for p in sysfs.glob('devcd*'):
   if p.name in baseline:continue
   try:
    failing=(p/'failing_device').resolve(strict=True)
    if failing!=device or (failing/'of_node').resolve(strict=True)!=node:continue
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
    with (p/'data').open('rb') as f:raw=f.read(4*1024*1024+1)
    assert len(raw)<=4*1024*1024,'Unexpectedly large dump; retain it'
    persist(root/('a5-'+p.name+'-private.bin'),raw);result.update(captured=True,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    assert (p/'failing_device').resolve(strict=True)==device
    (p/'data').write_bytes(b'1');deadline=time.monotonic()+2
    while p.exists() and time.monotonic()<deadline:time.sleep(.01)
    result['acknowledged']=not p.exists();assert result['acknowledged'];baseline.add(p.name)
   except FileNotFoundError:continue
  time.sleep(.01)
 result['timeout']=time.monotonic()-start>=600 and not (root/'collector-stop').exists()
except BaseException:result['error']=traceback.format_exc()
finally:
 result.update(terminal=True,seconds=round(time.monotonic()-start,3));persist(root/'collector-result.json',json.dumps(result,indent=2).encode())
