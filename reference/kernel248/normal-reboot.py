"""Single normal Linux restart, following the current183 EUD retirement sequence."""
from pathlib import Path
import ctypes,fcntl,json,mmap,os,struct,sys,time
r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(r/'k247-runtime/boot-id-private.txt').read_bytes() and os.uname().machine=='aarch64' and os.uname().version.startswith('#183 ')
s=json.loads((r/'k248-quiesce/state-private.json').read_text());proof=json.loads((r/'k248-quiesce/summary.json').read_text());assert s['terminal'] and s['exit_code']==0 and proof['taint']==0
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and all((p/'state').read_text().strip()=='offline' for p in Path('/sys/class/remoteproc').glob('*'))
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text() and len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines())==1
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0' and not Path('/proc/asound/card0').exists()
for addr in ['1-0039','1-003a']:assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices',addr,'status').read_text()
assert not Path('/etc/samurai-rootfs-release').exists() and Path('/etc/samurai-rootfs-release.k248-before-rescue').is_file()
device=Path('/sys/bus/platform/devices/88e0000.serial');assert (device/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom_eud_com')
assert (device/'of_node/reg').read_bytes()==struct.pack('>IIII',0,0x088e0000,0,0x2000) and (device/'of_node/compatible').read_bytes()==b'qcom,sm8150-eud-com\0' and os.sysconf('SC_PAGE_SIZE')==4096
fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC);rootfd=None;frozen=False;phase=Path('/run/k248-reboot-phase-private.json');assert not phase.exists()
try:
 with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE,offset=0x088e1000) as csr:
  before=struct.unpack_from('<I',csr,0x14)[0];assert (before&255) in [0,1]
  if sys.argv[1:]==['--inspect']:
   print(json.dumps(dict(stage=248,current_boot_guard_pass=True,quiesce_pass=True,normal_restart_only=True,eud_csr_low_byte=before&255,inspect_only=True)),flush=True);raise SystemExit(0)
  assert not sys.argv[1:];rootfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
  fcntl.ioctl(rootfd,0xc0045877,0);frozen=True
  record=dict(stage=248,state='filesystem_frozen',normal_restart=True,request_count=1);phase.write_text(json.dumps(record)+'\n')
  print(json.dumps(record),flush=True);time.sleep(0.5)
  Path('/sys/bus/platform/drivers/qcom_eud_com/unbind').write_text(device.name);assert not (device/'driver').exists()
  struct.pack_into('<I',csr,0x14,0);assert struct.unpack_from('<I',csr,0x14)[0]&255==0
  record.update(state='before_single_normal_restart',eud_console_unbound=True,eud_disable_readback=True);phase.write_text(json.dumps(record)+'\n');print(json.dumps(record),flush=True)
 libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long;libc.syscall.argtypes=[ctypes.c_long,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
 time.sleep(0.5);result=libc.syscall(142,0xfee1dead,672274793,0x01234567,None)
 raise RuntimeError('Normal reboot returned: '+str((result,ctypes.get_errno())))
except Exception:
 if frozen:fcntl.ioctl(rootfd,0xc0045878,0)
 raise
finally:
 if rootfd is not None:os.close(rootfd)
 os.close(fd)
