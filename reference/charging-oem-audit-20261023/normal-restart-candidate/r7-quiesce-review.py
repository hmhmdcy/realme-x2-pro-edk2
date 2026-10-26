# REVIEW CANDIDATE ONLY. New R7 transaction; same validated hardware quiesce.
"""Explicit quiesce for one RESTART2 bootloader transition; not run by this audit."""
from pathlib import Path
import ctypes,dbus,json,os,signal,subprocess,time,traceback

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

assert sys.argv[3]=='--commit-quiesce'
os.umask(0o077);assert not o.exists();o.mkdir(mode=0o700)
state=dict(work='charging-r7-restart',transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],state='preflight',terminal=False,pid=os.getpid());error=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def command(args,timeout=30):
 x=subprocess.run(args,capture_output=True,timeout=timeout)
 with (o/'commands-private.log').open('ab') as f:f.write(('ARGS '+repr(args)+'\n').encode()+x.stdout+x.stderr)
 assert x.returncode==0,(args,x.returncode)
def stop_service(name):
 x=subprocess.run(['rc-service',name,'status'],capture_output=True,timeout=10)
 if x.returncode==0:command(['rc-service',name,'stop'])
save();before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before)
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot.decode().strip()==meta['boot_id']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not phase.exists()
 assert (Path('/etc/samurai-rootfs-release')).is_file()
 assert not json.loads((r/'gnss-assist/watch-state.json').read_text())['active']
 if subprocess.run(['pgrep','-x','ModemManager'],capture_output=True).returncode==0:
  bus=dbus.SystemBus(private=True)
  objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
  assert all(int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled'])==0 for v in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v)
  bus.close()
 (o/'boot-id-private.txt').write_bytes(boot);state.update(state='stopping_services');save()
 command(['/usr/sbin/samurai-charging','stop'])
 for name in ['samurai-charging','samurai-gnss-assist','bluetooth','greetd','chronyd','networkmanager','iio-sensor-proxy','samurai-ssc']:stop_service(name)
 pids=subprocess.run(['pgrep','-u','10000'],capture_output=True).stdout.split()
 for value in pids:
  try:os.kill(int(value),signal.SIGTERM)
  except ProcessLookupError:pass
 time.sleep(2)
 for value in subprocess.run(['pgrep','-u','10000'],capture_output=True).stdout.split():
  try:os.kill(int(value),signal.SIGKILL)
  except ProcessLookupError:pass
 assert subprocess.run(['pgrep','-u','10000'],capture_output=True).returncode==1
 for p in Path('/proc').glob('[0-9]*/fd'):
  try:
   for f in p.iterdir():
    try:target=os.readlink(f)
    except OSError:continue
    assert not target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev'))
  except (FileNotFoundError,PermissionError):pass
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  if (p/'name').read_text().strip() in ['cam-front-vana','cam-front-vdig','cam-rear-vana','cam-rear-vdig','cam-tele-vana','cam-tele-vdig','cam-main-vana','cam-main-vdig','cam-main-vaf']:
   assert (p/'state').read_text().strip()=='disabled' and (p/'num_users').read_text().strip()=='0'
 for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):assert p.read_text().strip()=='closed'
 for addr in ['1-0039','1-003a']:assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices',addr,'status').read_text()
 stop_service('elogind');stop_service('modemmanager')
 for name in ['wpa_supplicant','ModemManager']:
  for value in subprocess.run(['pgrep','-x',name],capture_output=True).stdout.split():
   pid=int(value);assert Path('/proc',str(pid),'comm').read_text().strip()==name;os.kill(pid,signal.SIGTERM)
 time.sleep(1)
 assert subprocess.run(['pgrep','-x','ModemManager'],capture_output=True).returncode==1
 command(['/usr/sbin/samurai-bluetooth','stop'])
 wifi=Path('/sys/bus/platform/devices/18800000.wifi')
 if (wifi/'driver').exists():
  assert (wifi/'driver').resolve().name=='ath10k_snoc';(wifi/'driver/unbind').write_text(wifi.name)
 assert not (wifi/'driver').exists() and not Path('/sys/class/net/wlan0').exists()
 state.update(state='wifi_detached_stopping_dsps');save()
 for name in ['modem','adsp','slpi']:
  p=next(p for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()==name)
  if (p/'state').read_text().strip()=='running':(p/'state').write_text('stop')
  assert (p/'state').read_text().strip()=='offline'
 assert not Path('/proc/asound/card0').exists() and Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
 clients=Path('/sys/kernel/debug/dri/1/clients').read_text();assert len(clients.splitlines())==1;(o/'drm-clients-private.txt').write_text(clients)
 vt=Path('/sys/class/vtconsole/vtcon1');assert '(M) frame buffer device' in (vt/'name').read_text();(vt/'bind').write_text('0')
 Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').write_text('N')
 class Resources(ctypes.Structure):
  _fields_=[('count_fbs',ctypes.c_int),('fbs',ctypes.POINTER(ctypes.c_uint32)),('count_crtcs',ctypes.c_int),('crtcs',ctypes.POINTER(ctypes.c_uint32)),('count_connectors',ctypes.c_int),('connectors',ctypes.POINTER(ctypes.c_uint32)),('count_encoders',ctypes.c_int),('encoders',ctypes.POINTER(ctypes.c_uint32)),('min_width',ctypes.c_uint32),('max_width',ctypes.c_uint32),('min_height',ctypes.c_uint32),('max_height',ctypes.c_uint32)]
 lib=ctypes.CDLL('libdrm.so.2',use_errno=True);lib.drmModeGetResources.argtypes=[ctypes.c_int];lib.drmModeGetResources.restype=ctypes.POINTER(Resources);lib.drmModeFreeResources.argtypes=[ctypes.POINTER(Resources)];lib.drmSetMaster.argtypes=[ctypes.c_int];lib.drmModeSetCrtc.argtypes=[ctypes.c_int,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
 assert Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve()==Path('/dev/dri/card1')
 fd=os.open('/dev/dri/card1',os.O_RDWR|os.O_CLOEXEC)
 try:
  assert lib.drmSetMaster(fd)==0;res=lib.drmModeGetResources(fd);assert res and 0<res.contents.count_crtcs<=16
  try:
   crtcs=[res.contents.crtcs[i] for i in range(res.contents.count_crtcs)]
   for crtc in crtcs:assert lib.drmModeSetCrtc(fd,crtc,0,0,0,None,0,None)==0
  finally:lib.drmModeFreeResources(res)
 finally:os.close(fd)
 for i in range(3):
  time.sleep(1);text=Path('/sys/kernel/debug/dri/1/state').read_text();(o/('drm-idle-'+str(i)+'-private.txt')).write_text(text);assert 'active=1' not in text
 command(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
 after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after);faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()};assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 report=dict(work='charging-r7-restart',transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],all_remoteprocs_offline=True,display_inactive=True,audio_closed_and_muted=True,sensor_power_off=True,camera_providers_retained=True,wlan_driver_detached=True,source_nv_hashes_preserved=True,taint=0,fault_delta=faults,restart2_bootloader_expected=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(o/'failure-private.txt').write_text(error);state.update(state='failed',terminal=True,exit_code=1);save()
if error:raise SystemExit(1)
