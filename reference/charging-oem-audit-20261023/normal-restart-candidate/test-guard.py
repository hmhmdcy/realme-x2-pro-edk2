"""Offline exact emitted guard checks; no real /proc, device, or MMIO access."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare',HERE/'prepare.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
sha=lambda value:hashlib.sha256(value).hexdigest()
release='7.3.0-rc6-rmx1931-samurai-k363+'
module='/lib/modules/'+release+'/extra/samurai-charging/samurai-usb-input.ko'
manifest='/usr/share/samurai-charging/manifest.json'
boot='11111111-2222-3333-4444-555555555555'
uname=types.SimpleNamespace(machine='aarch64',release=release,version='#363 exact fixture')
meta={'schema':'samurai-r7-restart-review-v1','transaction_id':'charging-r7-test-fixture',
 'boot_id':boot,'kernel_release':release,'kernel_version':uname.version,
 'rootfs_release_sha256':sha(b'ROOTFS_ID=samurai-f2fs-rootfs01\n'),
 'disk_pair':{module:sha(b'R7ko'),manifest:''},'old_loaded_usb_note_sha256':sha(b'old-R6-note')}
manifest_bytes=json.dumps({'release':release,'modules':{'samurai-usb-input':
 {'target':module,'sha256':meta['disk_pair'][module]}},'installed_files':{module:meta['disk_pair'][module]}}).encode()
meta['disk_pair'][manifest]=sha(manifest_bytes)
files={module:b'R7ko',manifest:manifest_bytes,
 '/etc/samurai-rootfs-release':b'ROOTFS_ID=samurai-f2fs-rootfs01\n',
 '/proc/sys/kernel/random/boot_id':(boot+'\n').encode(),'/proc/sys/kernel/tainted':b'0\n',
 '/sys/module/samurai_usb_input/notes/.note.gnu.build-id':b'old-R6-note',
 '/sys/module/samurai_usb_input/parameters/native_retained':b'Y\n'}
guard='/root/fresh-private.json'
stats={}
class FakePath:
 def __init__(self,*parts):self.path='/'.join(str(p).rstrip('/') for p in parts)
 def __str__(self):return self.path
 def __truediv__(self,value):return FakePath(self.path,value)
 def is_absolute(self):return self.path.startswith('/')
 def is_file(self):return self.path in files
 def is_symlink(self):return stats.get(self.path,{}).get('symlink',False)
 def stat(self):return types.SimpleNamespace(st_uid=stats.get(self.path,{}).get('uid',0),st_mode=stats.get(self.path,{}).get('mode',0o100600))
 def read_bytes(self):return files[self.path]
 def read_text(self):return self.read_bytes().decode()
 def exists(self):return self.path in files

def execute(m=None,u=None):
 files[guard]=json.dumps(m or meta).encode()
 with patch.object(sys,'argv',['worker','--guard',guard,'--inspect']):
  exec(mod.GUARD,{'Path':FakePath,'json':json,'os':types.SimpleNamespace(uname=lambda:u or uname)})

passed=0
def expect(label,change=None,edit=None,accepted=False,u=None):
 global passed
 original=copy.deepcopy(files);oldstats=copy.deepcopy(stats);m=copy.deepcopy(meta)
 try:
  if change:change(m)
  if edit:edit()
  try:execute(m,u)
  except (AssertionError,KeyError):assert not accepted,label
  else:assert accepted,label
  passed+=1
 finally:files.clear();files.update(original);stats.clear();stats.update(oldstats)

expect('fresh disk R7 / resident R6',accepted=True)
expect('old boot',lambda m:m.update(boot_id='old'))
expect('old schema',lambda m:m.update(schema='old-recovery'))
expect('stale transaction path',lambda m:m.update(transaction_id='charging-20261023-recovery'))
expect('wrong exact kernel',lambda m:m.update(kernel_version='#363 other'))
expect('taint512',edit=lambda:files.update({'/proc/sys/kernel/tainted':b'512'}))
expect('not native retained',edit=lambda:files.update({'/sys/module/samurai_usb_input/parameters/native_retained':b'N'}))
expect('resident replaced',edit=lambda:files.update({'/sys/module/samurai_usb_input/notes/.note.gnu.build-id':b'new-R7-note'}))
expect('disk ko mismatch',edit=lambda:files.update({module:b'not-R7'}))
expect('manifest mismatch',edit=lambda:files.update({manifest:b'{}'}))
expect('extra disk target',lambda m:m['disk_pair'].update({'/dev/mem':sha(b'')}))
expect('rootfs mismatch',edit=lambda:files.update({'/etc/samurai-rootfs-release':b'other'}))
expect('symlink guard',edit=lambda:stats.update({guard:{'symlink':True}}))
expect('writable guard',edit=lambda:stats.update({guard:{'mode':0o100622}}))
expect('wrong owner',edit=lambda:stats.update({guard:{'uid':10000}}))
expect('existing phase',edit=lambda:files.update({'/run/charging-r7-test-fixture-reboot-phase-private.json':b'old'}))
expect('different architecture',u=types.SimpleNamespace(machine='x86_64',release=release,version=uname.version))
for name in ['r7-quiesce-review.py','r7-restart-review.py']:
 text=(HERE/name).read_text();ast.parse(text)
 assert 'original-private.json\').read_text' not in text
 assert 'strip()==\'512\'' not in text
restart=(HERE/'r7-restart-review.py').read_text()
assert restart.index("if sys.argv[3]=='--inspect'")<restart.index("os.open('/dev/mem'")
assert restart.index("phase.open('x')")<restart.index('fcntl.ioctl(rootfd,0xc0045877')
assert '0xa1b2c3d4' in restart and "b'bootloader\\0'" in restart
result={'passed':True,'guard_vectors':passed,'workers_parsed':2,
 'inspect_before_mmio_open':True,'exclusive_claim_before_freeze':True,
 'hardware_actions_executed':False,'plain_restart_validation':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
