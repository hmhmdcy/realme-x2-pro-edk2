# UNRUN TRANSPORT-TAIL REVIEW CANDIDATE. Never repeat the existing R7 transaction.
"""One explicitly committed RESTART2 bootloader transition, followed by host reboot."""
from pathlib import Path
import ctypes,fcntl,json,mmap,os,struct,sys,time

# NEW contract: root supplies a fresh, private R7 transaction guard. This is
# deliberately incompatible with original-private.json / old terminal workers.
import hashlib,re,sys
assert len(sys.argv)==4 and sys.argv[1]=='--guard'
guard_path=Path(sys.argv[2]);assert guard_path.is_absolute()
assert guard_path.is_file() and not guard_path.is_symlink()
assert guard_path.stat().st_uid==0 and not guard_path.stat().st_mode&0o022
meta=json.loads(guard_path.read_text())
assert meta['schema']=='samurai-r7-restart-review-v1'
assert re.fullmatch(r'charging-r7-[a-z0-9-]{8,64}',meta['transaction_id'])
assert meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert os.uname().machine=='aarch64'
assert os.uname().release==meta['kernel_release']
assert os.uname().version==meta['kernel_version']
assert os.uname().version.startswith('#363 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert hashlib.sha256(Path('/etc/samurai-rootfs-release').read_bytes()).hexdigest()==meta['rootfs_release_sha256']
module_path='/lib/modules/'+meta['kernel_release']+'/extra/samurai-charging/samurai-usb-input.ko'
manifest_path='/usr/share/samurai-charging/manifest.json'
assert set(meta['disk_pair'])=={module_path,manifest_path}
for name,digest in meta['disk_pair'].items():
 p=Path(name);assert p.is_file() and not p.is_symlink()
 assert p.stat().st_uid==0 and not p.stat().st_mode&0o022
 assert re.fullmatch(r'[0-9a-f]{64}',digest)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
manifest=json.loads(Path(manifest_path).read_text())
assert manifest['release']==meta['kernel_release']
assert manifest['modules']['samurai-usb-input']['target']==module_path
assert manifest['modules']['samurai-usb-input']['sha256']==meta['disk_pair'][module_path]
assert manifest['installed_files'][module_path]==meta['disk_pair'][module_path]
# The disk module is R7, while the current live native provider must still be
# the old accepted R6 module. No unload or replacement is attempted here.
assert hashlib.sha256(Path('/sys/module/samurai_usb_input/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['old_loaded_usb_note_sha256']
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
r=Path('/var/lib/samurai');o=r/meta['transaction_id']
phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json')
assert not phase.exists()

assert sys.argv[3] in ['--inspect','--commit-restart2-bootloader']
s=json.loads((o/'state-private.json').read_text());proof=json.loads((o/'summary.json').read_text());assert s['terminal'] and s['exit_code']==0 and proof['taint']==0
assert s['boot_id']==proof['boot_id']==meta['boot_id']
assert s['transaction_id']==proof['transaction_id']==meta['transaction_id']
assert (o/'boot-id-private.txt').read_text().strip()==meta['boot_id']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and all((p/'state').read_text().strip()=='offline' for p in Path('/sys/class/remoteproc').glob('*'))
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text() and len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines())==1
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0' and not Path('/proc/asound/card0').exists()
for addr in ['1-0039','1-003a']:assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices',addr,'status').read_text()
assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()
device=Path('/sys/bus/platform/devices/88e0000.serial');assert (device/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom_eud_com')
assert (device/'of_node/reg').read_bytes()==struct.pack('>IIII',0,0x088e0000,0,0x2000) and (device/'of_node/compatible').read_bytes()==b'qcom,sm8150-eud-com\0' and os.sysconf('SC_PAGE_SIZE')==4096
if sys.argv[3]=='--inspect':
 print(json.dumps(dict(work='charging-r7-restart',current_boot_guard_pass=True,quiesce_pass=True,restart2_bootloader_expected=True,inspect_only=True,csr_not_read=True)),flush=True);raise SystemExit(0)
fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC);rootfd=None;frozen=False
libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long;libc.syscall.argtypes=[ctypes.c_long,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
command=ctypes.create_string_buffer(b'bootloader\0')
try:
 with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE,offset=0x088e1000) as csr:
  before=struct.unpack_from('<I',csr,0x14)[0];assert (before&255) in [0,1]
  assert sys.argv[3]=='--commit-restart2-bootloader';rootfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
  with phase.open('x') as claim:json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],state='claimed_once',request_count=1),claim)
  os.sync()
  fcntl.ioctl(rootfd,0xc0045877,0);frozen=True
  record=dict(work='charging-r7-restart',transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],state='filesystem_frozen_restart2_armed',restart2_bootloader=True,request_count=1);phase.write_text(json.dumps(record)+'\n')
  print(json.dumps(record),flush=True);time.sleep(0.5)
  Path('/sys/bus/platform/drivers/qcom_eud_com/unbind').write_text(device.name);assert not (device/'driver').exists()
  struct.pack_into('<I',csr,0x14,0);assert struct.unpack_from('<I',csr,0x14)[0]&255==0
  # After retirement, transport output, JSON writes, sleep and mmap close
  # must not stand between the confirmed CSR readback and this one syscall.
  result=libc.syscall(142,0xfee1dead,672274793,0xa1b2c3d4,ctypes.cast(command,ctypes.c_void_p))
  raise RuntimeError('Restart2 bootloader returned: '+str((result,ctypes.get_errno())))
except Exception:
 if frozen:fcntl.ioctl(rootfd,0xc0045878,0)
 raise
finally:
 if rootfd is not None:os.close(rootfd)
 os.close(fd)
