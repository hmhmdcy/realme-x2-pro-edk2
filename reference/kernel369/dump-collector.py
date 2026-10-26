"""Persist only this A5 device's bounded devcoredump, then acknowledge it."""
from pathlib import Path
import argparse,json,os,re,time
from dump_decoder import decode

def persist(path,data):
 with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)

def collect(root,sysfs,dt_base,seconds=15):
 os.umask(0o077)
 expected=dt_base/'soc@0/samurai-icp356-boot@ac10000'
 baseline={p.name for p in sysfs.glob('devcd*')};start=time.monotonic()
 persist(root/'collector-ready.json',json.dumps(dict(pid=os.getpid(),ready=True,baseline_names=sorted(baseline))).encode())
 result=dict(pid=os.getpid(),terminal=False,captured=False,owned_snapshot_acknowledged=False)
 try:
  while time.monotonic()-start<seconds and not (root/'collector-stop').exists():
   for candidate in sysfs.glob('devcd*'):
    if candidate.name in baseline or not re.fullmatch(r'devcd\d+',candidate.name):continue
    try:
     failing=(candidate/'failing_device').resolve(strict=True)
     if failing.name!='ac10000.samurai-icp356-boot' or (failing/'of_node').resolve(strict=True)!=expected:continue
     with (candidate/'data').open('rb') as stream:raw=stream.read(569)
    except FileNotFoundError:continue
    path=root/('a5-'+candidate.name+'-private.bin');persist(path,raw)
    result.update(captured=True,name=candidate.name,bytes=len(raw),raw_private_path=str(path))
    try:
     decoded=decode(raw);persist(root/'a5-dump-decoded-private.json',json.dumps(decoded,indent=2).encode())
     result.update(decoded=True,init_response=decoded['init_response'],sfr_characters=len(decoded['sfr']))
    except (ValueError,UnicodeError) as error:result.update(decoded=False,decode_error=str(error))
    # This standard acknowledgement releases devcoredump's failing-device ref
    # before the owner removes its temporary OF overlay. Never disable globally.
    with (candidate/'data').open('wb') as stream:stream.write(b'1')
    deadline=time.monotonic()+2
    while candidate.exists() and time.monotonic()<deadline:time.sleep(.005)
    result['owned_snapshot_acknowledged']=not candidate.exists()
    if not result['owned_snapshot_acknowledged']:raise RuntimeError('Owned devcoredump still retains its device reference')
    return result
   time.sleep(.005)
  result['timeout']=not (root/'collector-stop').exists();return result
 except BaseException as error:
  result['error']=str(error);return result
 finally:
  result.update(terminal=True,seconds=round(time.monotonic()-start,3))
  persist(root/'collector-result.json',json.dumps(result,indent=2).encode())

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--sysfs',type=Path,default=Path('/sys/class/devcoredump'));parser.add_argument('--dt-base',type=Path,default=Path('/sys/firmware/devicetree/base'));parser.add_argument('--seconds',type=float,default=15)
 args=parser.parse_args();collect(args.root,args.sysfs,args.dt_base,args.seconds)
