from pathlib import Path
import host
import json

here = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess
root=Path('/var/lib/samurai');base=root/'k226-baseline';out=root/'k226-final-health'
assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
bus=dbus.SystemBus(private=True)
assert str(bus.get_name_owner('org.freedesktop.ModemManager1'))==(base/'mm-owner-private.txt').read_text()
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(base/'modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties')
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');gps=dict(enabled=int(loc['Enabled']),signals=bool(loc['SignalsLocation']),rate=int(loc['GpsRefreshRate']))
assert gps==dict(enabled=0,signals=False,rate=30)
modem={k:int(props.Get('org.freedesktop.ModemManager1.Modem',k)) for k in ['State','StateFailedReason','PowerState']}
assert modem==dict(State=-1,StateFailedReason=2,PowerState=1)
blue=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[v['org.bluez.Adapter1'] for v in blue.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in blue.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());oldwatch=json.loads((base/'watch-before-private.json').read_text())
assert watch['running'] and not watch['active'] and all(watch[k]==oldwatch[k] for k in ['worker_starts','worker_completions'])
assert watch['worker_starts']==watch['worker_completions']==0
(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert rp==dict(adsp='running',slpi='running',modem='running')
for name in ['7-0010','acb3000.camss','ac4b000.cci']:
 p=Path('/sys/bus/i2c/devices' if name=='7-0010' else '/sys/bus/platform/devices')/name
 assert (p/'power/runtime_status').read_text().strip()=='suspended'
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name in ['cam-front-vdig','cam-front-vana']:rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
assert len(rails)==2 and all(v==dict(state='disabled',num_users='0') for v in rails.values())
for kind in ['default','high']:
 state=json.loads((root/('k226-loc-r3-'+kind)/'state-private.json').read_text());assert state['terminal'] and state['exit_code']==0
 assert not (Path('/proc')/str(state['pid'])).exists()
 assert state['cleanup']['stop_ack'] and state['cleanup']['client_released'] and state['cleanup']['device_closed']
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
with (out/'nv-check-private.txt').open('wb') as f:subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
clock=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10);(out/'chrony-private.txt').write_text(clock.stdout+clock.stderr);assert clock.returncode==0 and 'Normal' in clock.stdout
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
raw=subprocess.run(['qmicli','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=20);(out/'dms-private.txt').write_bytes(raw.stdout+raw.stderr);assert raw.returncode==0 and b"Mode: 'shutting-down'" in raw.stdout
report=dict(stage=226,same219_boot=True,kernel183_and_r13_r8_deployment_preserved=True,gps=gps,
 modem=modem,user_confirmed_no_sim=True,dms_operating_mode='shutting-down',
 official_both_sessions_stopped_clients_released_devices_closed=True,no_loc_session_process_left=True,
 gps_engine_off_observed_on_both_stops=True,watch_idle_and_worker_counts_preserved=True,
 remoteprocs=rp,taint=0,fault_counts=faults,nv_sources_unchanged=True,chrony_normal=True,
 camera_devices_suspended=True,front_rails_off_zero_users=True,experimental_full_mode_disabled=True,
 bt_powered=False,bt_connections=0,installed_mm191_binary_preserved=True,
 no_nv_write_flash_reboot_or_dms_power_change=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=75)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(run.stdout + run.stderr)
report = json.loads(run.stdout)
(here / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
