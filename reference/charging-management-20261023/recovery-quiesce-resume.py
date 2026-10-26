from pathlib import Path
import ctypes,dbus,json,os,signal,subprocess,time,traceback
o=Path('/var/lib/samurai/charging-20261023-recovery')
previous=json.loads((o/'state-private.json').read_text())
assert previous['terminal'] and previous['exit_code']==1
failure=(o/'failure-private.txt').read_text()
assert "num_users" in failure and "512" in failure
assert not (o/'initial-failure-private.txt').exists()
(o/'failure-private.txt').rename(o/'initial-failure-private.txt')
r=Path('/var/lib/samurai');os.umask(0o077)
state=dict(stage=367,state='preflight',terminal=False,pid=os.getpid());error=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def command(args,timeout=30):
 x=subprocess.run(args,capture_output=True,timeout=timeout)
 with (o/'commands-private.log').open('ab') as f:f.write(('ARGS '+repr(args)+'\n').encode()+x.stdout+x.stderr)
 assert x.returncode==0,(args,x.returncode)
def stop_service(name):
 x=subprocess.run(['rc-service',name,'status'],capture_output=True,timeout=10)
 if x.returncode==0:command(['rc-service',name,'stop'])
save();before=subprocess.check_output(['dmesg'])
try:
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
 after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after);faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()};assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
 report=dict(stage=367,all_remoteprocs_offline=True,display_inactive=True,audio_closed_and_muted=True,sensor_power_off=True,camera_providers_retained=True,wlan_driver_detached=True,source_nv_hashes_preserved=True,taint=512,fault_delta=faults,restart2_bootloader_expected=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(o/'failure-private.txt').write_text(error);state.update(state='failed',terminal=True,exit_code=1);save()
if error:raise SystemExit(1)
