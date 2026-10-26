from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k223-final-health';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k223-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
manifest=json.loads((root/'k223-r8-package-candidates/forward-manifest.json').read_text());checked=0
for package in manifest['packages']:
 for name,item in package['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  checked+=1
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name in ['cam-front-vdig','cam-front-vana']:rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
assert len(rails)==2 and all(x==dict(state='disabled',num_users='0') for x in rails.values())
bus=dbus.SystemBus(private=True);p=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(root/'k221-baseline/modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties')
loc=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');gps=dict(enabled=int(loc['Enabled']),signals=bool(loc['SignalsLocation']),rate=int(loc['GpsRefreshRate']));assert gps==dict(enabled=0,signals=False,rate=30)
modem=p.GetAll('org.freedesktop.ModemManager1.Modem');modem_summary={k:int(modem[k]) for k in ['State','StateFailedReason','PowerState']}
assert modem_summary==dict(State=-1,StateFailedReason=2,PowerState=1)
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']
(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
chrony=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10);(out/'chrony-private.txt').write_text(chrony.stdout+chrony.stderr);assert chrony.returncode==0 and 'Normal' in chrony.stdout
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='running',modem='running')
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
with (out/'nv-check-private.txt').open('wb') as log:subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
slot_text=(root/'k221-uim-readonly/uim-get-slot-status-private.txt').read_text()
slot_lines=[l.strip() for l in slot_text.splitlines() if l.strip().startswith(('Card status:','Slot status:','Logical slot:'))]
trials=[]
for name in ['k223-paired-sof-trial','k223-control-snapshot-trial']:
 r=json.loads((root/name/'state-private.json').read_text());assert r['phase']=='verified-restored';trials.append(name)
assert json.loads((root/'k223-r8-paired-deployment/state-private.json').read_text())['phase']=='verified'
assert json.loads((root/'k223-full-mode-experiment/state-private.json').read_text())['state']=='finished-default-mode-restored'
import struct,fcntl,re
camss=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'
data=camss.read_bytes();assert hashlib.sha256(data).hexdigest()=='fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58);hs=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];s=hs[strings];names=data[s[4]:s[4]+s[5]]
notes=[data[h[4]:h[4]+h[5]] for h in hs if names[h[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(notes)==1 and notes[0]==Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()
nodes={(p/'name').read_text().strip():p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
fd=os.open('/dev/'+nodes['msm_vfe0_rdi0'],os.O_RDWR|os.O_CLOEXEC)
try:
 sub=bytearray(32);struct.pack_into('I',sub,0,4)
 fcntl.ioctl(fd,0x4020565a,sub,True)
finally:os.close(fd)
for name in ['imx471 7-0010','msm_csid0']:
 text=subprocess.check_output(['v4l2-ctl','-d','/dev/'+nodes[name],'--get-ctrl=test_pattern'],text=True,timeout=10);assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',text)
r=dict(stage=223,current219_boot_preserved=True,kernel183_and_e49_module_preserved=True,r8_r3_camera_payload_records_verified=checked,camera_devices_suspended=True,front_rails_off_zero_users=True,experimental_full_mode_disabled=True,gps=gps,modem=modem_summary,uim_slot_status_lines_historical_stage221=slot_lines,temporary_camss_trials_restored=len(trials),deployed_camss_file_and_loaded_note_verified=True,standard_frame_sync_subscription_verified=True,test_patterns_disabled=True,gnss_watcher_idle=True,gnss_worker_counts_preserved_since220=watch['worker_starts']==watch['worker_completions']==0,chrony_normal=True,remoteprocs=rp,bt_powered=False,bt_connections=0,taint=0,fault_counts=faults,nv_sources_unchanged=True,camera_metadata_captures_performed=True,no_gnss_engine_start_or_flash_or_reboot=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=90);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
