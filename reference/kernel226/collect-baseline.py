from pathlib import Path
import host
import json

here = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k226-baseline'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k225-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
if out.exists():
 assert not (out/'summary.json').exists() and (out/'boot-id-private.txt').read_bytes()==boot
else:
 out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
before=subprocess.check_output(['dmesg']);(out/'dmesg-resume-before-private.txt').write_bytes(before)
bus=dbus.SystemBus(private=True)
manager=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager')
objects=manager.GetManagedObjects();modems=[str(k) for k,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(modems)==1
modem=modems[0];(out/'modem-path-private.txt').write_text(modem)
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',modem),'org.freedesktop.DBus.Properties')
location=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(location['Enabled'])==0 and not location['SignalsLocation']
power={k:int(props.Get('org.freedesktop.ModemManager1.Modem',k)) for k in ['State','StateFailedReason','PowerState']}
(out/'location-before-private.json').write_text(json.dumps(location,default=str,indent=2)+'\n')
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active']
(out/'watch-before-private.json').write_text(json.dumps(watch,indent=2)+'\n')
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));(out/'mm-owner-private.txt').write_text(owner)
bus.close()
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert rp==dict(adsp='running',slpi='running',modem='running')
camera={};installed={}
for block in Path('/lib/apk/db/installed').read_text().strip().split('\n\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if line.startswith(('P:','V:')))
 if 'P' in fields:installed[fields['P']]=fields['V']
for name in ['libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:
 camera[name]=installed[name]
 assert installed[name]==('99990.7.2-r13' if name.startswith('libcamera') else '0.1.0-r8')
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
for name in ['7-0010','acb3000.camss','ac4b000.cci']:
 base=Path('/sys/bus/i2c/devices' if name=='7-0010' else '/sys/bus/platform/devices')/name
 assert (base/'power/runtime_status').read_text().strip()=='suspended'
raw=subprocess.run(['qmicli','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=20)
(out/'dms-operating-mode-private.txt').write_bytes(raw.stdout+raw.stderr)
text=raw.stdout.decode(errors='replace');assert raw.returncode==0
mode=next((s.split("Mode: '",1)[1].split("'",1)[0] for s in text.splitlines() if "Mode: '" in s),None);assert mode
after=subprocess.check_output(['dmesg']);faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
report=dict(stage=226,same219_boot_authenticated=True,kernel183_r13_r8_preserved=True,current_guard_created=True,
 gps_enabled=int(location['Enabled']),gps_signals=bool(location['SignalsLocation']),gps_refresh=int(location['GpsRefreshRate']),
 gnss_watcher_idle=True,modem=power,dms_operating_mode=mode,user_confirmed_no_sim=True,
 camera_devices_suspended=True,experimental_full_mode_disabled=True,remoteprocs=rp,taint=0,fault_delta=faults,
 no_engine_start_power_change_or_reboot=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=75)
(host.PRIVATE / 'baseline-host-private.log').write_bytes(run.stdout + run.stderr)
report = json.loads(run.stdout)
(here / 'baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = dict(stage=226,full_peripheral_goal_active=True,
    previous_goal_turn_classification='progress:225 r13/r8 native controls accepted, canonical locks and8257-file mirror closed; three research reports changed next experiments',
    state='Fresh authenticated baseline recorded; GNSS session accuracy experiment not yet started',
    guard='/var/lib/samurai/k226-baseline/boot-id-private.txt',transition_pending=False,
    active_native_session=None,active_build_session=None,user_confirmed_no_sim=True,
    next='Build/review bounded same-CID LOC criteria and accuracy A/B tool; preserve current phone payloads')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
archive=here.parents[1]/'archive/NEXT-SESSION-through225-2026-10-16.md'
assert not archive.exists();archive.write_bytes((here.parents[1]/'NEXT-SESSION.md').read_bytes())
print(json.dumps(report))
