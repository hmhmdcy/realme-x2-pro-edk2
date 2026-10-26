from pathlib import Path
import hashlib,host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k222-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k221-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
assert not out.exists();out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
manifest=json.loads((root/'k220-r7-package-candidates/forward-manifest.json').read_text());checked=0
for package in manifest['packages']:
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
  checked+=1
(out/'installed-before-private.txt').write_bytes(Path('/lib/apk/db/installed').read_bytes());(out/'world-before-private.txt').write_bytes(Path('/etc/apk/world').read_bytes())
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
before=subprocess.check_output(['dmesg']);media=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(out/'media-before-private.txt').write_bytes(media)
p=subprocess.run(['cam','--camera','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10','--list-controls','--list-properties','--info'],env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO'),preexec_fn=demote,capture_output=True,timeout=20)
(out/'camera-info-stdout-private.txt').write_bytes(p.stdout);(out/'camera-info-stderr-private.txt').write_bytes(p.stderr);assert p.returncode==0
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'];assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert media==subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='running',modem='running')
lines=[l for l in p.stdout.decode().splitlines() if any(x in l for x in ['Contrast','Gamma','Exposure','AnalogueGain','PixelArray','ScalerCrop'])]
r=dict(stage=222,same219_boot_freshly_authenticated=True,guard_created=True,installed_r7_payload_records_verified=checked,
 sensor_timing_module219_preserved=True,experimental_full_mode_disabled=True,camera_info_exit=0,selected_control_and_property_lines=lines,
 media_graph_preserved=True,camera_devices_suspended=True,remoteprocs=rp,taint=0,fault_delta=faults,no_capture_or_reboot=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60);(host.PRIVATE/'baseline-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(guard='/var/lib/samurai/k222-baseline/boot-id-private.txt',state='Current219 boot/module/r7 payloads and idle state authenticated; inspecting API and per-mode IPA timing')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
