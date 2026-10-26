"""Actual frozen identity functions only. Default never reads the device."""
from pathlib import Path
import base64, hashlib, json, os, re, stat, sys, time
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def attempt(fn):
 try:return fn()
 except Exception as e:return {'error':type(e).__name__,'message':str(e),'errno':getattr(e,'errno',None)}

def read(path):return attempt(lambda:Path(path).read_text().strip())

def file_fact(path):
 p=Path(path);raw=p.read_bytes();s=p.lstat()
 return {'path':str(p),'resolved':str(p.resolve()),'sha256':sha(raw),
  'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,
  'regular':stat.S_ISREG(s.st_mode),'symlink':p.is_symlink()}

def check_file(f,digest):
 assert f['sha256']==digest and f['regular'] and not f['symlink']
 assert f['uid']==0 and not f['mode']&0o022

def identity():
 return {'boot_id':read('/proc/sys/kernel/random/boot_id'),
  'uname':dict(zip(['sysname','nodename','release','version','machine'],os.uname())),
  'rootfs':attempt(lambda:file_fact('/etc/samurai-rootfs-release')),
  'serial_sha256':attempt(lambda:sha(Path('/sys/devices/soc0/serial_number').read_bytes())),
  'compatible_b64':attempt(lambda:base64.b64encode(Path('/sys/firmware/devicetree/base/compatible').read_bytes()).decode()),
  'taint':read('/proc/sys/kernel/tainted')}

def check_identity(r,g):
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',r['boot_id'])
 assert r['boot_id']!=g['boot_id'],'still old boot'
 assert r['uname']['machine']=='aarch64' and r['taint']=='0'
 assert r['uname']['release']==g['kernel_release']=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert r['uname']['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
 check_file(r['rootfs'],g['rootfs_release_sha256'])
 assert r['serial_sha256']==g['soc_serial_sha256']
 compatible=base64.b64decode(r['compatible_b64'],validate=True)
 assert sha(compatible)==g['compatible_sha256'] and b'realme,samurai' in compatible.split(b'\0')
 return {'new_boot':True,'same_board_release_rootfs_new_Image502':True}

def main(request=None):
 if sys.flags.optimize:raise RuntimeError('optimized Python is unsupported')
 if request is None:
  print(json.dumps({'source_only':True,'device_accessed':False}));return 0
 assert request['schema']=='samurai-irq-postboot-identity-probe-v1'
 started=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
 before=identity();check_identity(before,request['guard'])
 after=identity();check_identity(after,request['guard'])
 assert before['boot_id']==after['boot_id']
 print(json.dumps({'schema':request['schema'],'request':request,
  'identity_before':before,'identity_after':after,'started_boottime_ns':started,
  'ended_boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)}),flush=True)
 return 0

if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
