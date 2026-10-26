"""Audit the clean in-tree boot against fresh and previous accepted inventories."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import dbus,hashlib,json,os,struct,subprocess
root=Path('/var/lib/samurai');out=root/'k230-final-health';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k230-runtime/boot-id-private.txt').read_bytes()
def check(args,label,cwd=None):
 p=subprocess.run(args,capture_output=True,timeout=35,cwd=cwd);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
check(['sha256sum','-c',str(root/'k230-baseline/partition-check.sha256')],'partitions')
check(['sha256sum','-c',str(root/'k230-baseline/userspace-check.sha256')],'userspace')
check(['sha256sum','-c',str(root/'k230-baseline/module-tree.sha256')],'module-tree',Path('/usr/lib/modules')/os.uname().release)
check(['sha256sum','-c',str(root/'k228-intree-stage/module-tree-after.sha256')],'prior-accepted-module-tree',Path('/usr/lib/modules')/os.uname().release)
check(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv')
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k230-baseline/installed-before-private.txt').read_bytes()
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k228-baseline/installed-before-private.txt').read_bytes()
assert (root/'k230-baseline/userspace-check.sha256').read_bytes()==(root/'k228-baseline/userspace-check.sha256').read_bytes()
assert int(Path('/proc/sys/kernel/tainted').read_text())==0
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={}
assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()==(root/'k230-baseline/fastrpc-default-note-private.bin').read_bytes()
assert int(Path('/sys/module/fastrpc/refcnt').read_text())==1
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/misc/fastrpc.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='2abde0ead81c2feb78f639da2ab29d7c3e29654a9d013a098418b232a5cfd794'
assert subprocess.check_output(['modinfo','-F','intree',str(module)],text=True).strip()=='Y'
check(['rc-service','samurai-ssc','status'],'ssc-status')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='running',modem='running')
bus=dbus.SystemBus(private=True)
props=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
has={n:bool(props.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values())
objs=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();paths=[p for p,v in objs.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',paths[0]),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=props.GetAll('org.freedesktop.ModemManager1.Modem')
gps=dict(enabled=int(loc['Enabled']),signals=bool(loc['SignalsLocation']),refresh_rate=int(loc['GpsRefreshRate']));assert gps==dict(enabled=0,signals=False,refresh_rate=30)
blue=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in blue.values() if 'org.bluez.Adapter1' in v];assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'];assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in blue.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared'] and watch['worker_starts']==watch['worker_completions']==0
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
for path in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']:assert Path(path,'power/runtime_status').read_text().strip()=='suspended'
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name in ['cam-front-vdig','cam-front-vana']:rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
assert len(rails)==2 and all(v==dict(state='disabled',num_users='0') for v in rails.values())
check(['chronyc','tracking'],'clock');clock=(out/'clock-private.log').read_text();assert 'Normal' in clock
wifi=subprocess.run(['iw','dev','wlan0','link'],capture_output=True,timeout=10);(out/'wifi-private.log').write_bytes(wifi.stdout+wifi.stderr)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
report=dict(stage=230,current_boot_guard_verified=True,boot219_logdump183_persist_nv_exact=True,
 module_default_intree='2abde0ea',running_intree_candidate='2abde0ea',runtime_refcount=1,clean_intree_boot_verified=True,
 module_tree786_and_unrelated785_exact=True,camera_e49_fae1_and_r13_r8_preserved=True,package_database_unchanged=True,
 taint=0,tainted_modules=[],fault_counts=faults,remoteprocs=rp,sensor_proxy=has,
 gps=gps,gnss_watch_idle=True,gnss_utc_auto_prepared=True,gnss_data_workers=0,
 aiding168h_is_previous_boot226_evidence_not_remeasured=True,modem_state=int(m['State']),modem_failed_reason=int(m['StateFailedReason']),modem_power_state=int(m['PowerState']),user_no_sim=True,
 bt_powered=False,bt_connections=0,camera_devices_suspended=True,front_rails_off_zero_users=True,fullres_experiment=False,
 chrony_normal=True,wifi_connected=b'Connected to' in wifi.stdout,no_active_transition=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=100)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(Path(__file__).resolve().parent / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
