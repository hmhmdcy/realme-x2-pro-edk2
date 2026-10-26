"""Strictly identify the new Linux boot and verify the diagnostic PID is live."""
from pathlib import Path
import dbus,json,os,subprocess
r=Path('/var/lib/samurai');base=r/'k244-nextboot';cfg=json.loads((base/'config-private.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot!=cfg['previous_boot'] and Path('/proc/device-tree/model').read_bytes().hex()==cfg['model_hex'] and os.uname().release==cfg['kernel_release']
runtime=r/'k244-runtime'
if not runtime.exists():runtime.mkdir(mode=0o700);(runtime/'boot-id-private.txt').write_text(boot+'\n')
assert (runtime/'boot-id-private.txt').read_text().strip()==boot
o=base/'capture';state=json.loads((o/'state-private.json').read_text()) if (o/'state-private.json').exists() else None;alive=False
if state:
 p=Path('/proc')/str(state['pid'])
 if p.exists():alive=p.joinpath('stat').read_text().split()[21]==str(state['start_ticks']) and b'/var/lib/samurai/k244-nextboot/boot-diag.py' in p.joinpath('cmdline').read_bytes().split(b'\0')
bus=dbus.SystemBus(private=True);mm={}
if bus.name_has_owner('org.freedesktop.ModemManager1'):
 objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 for p,v in objects.items():
  if 'org.freedesktop.ModemManager1.Modem' in v:mm=dict(state=int(v['org.freedesktop.ModemManager1.Modem']['State']),power=int(v['org.freedesktop.ModemManager1.Modem']['PowerState']),location_enabled=int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled']))
bus.close();report=dict(stage=244,new_boot_confirmed=True,kernel_release=os.uname().release,taint=int(Path('/proc/sys/kernel/tainted').read_text()),diag_state=state,diag_pid_live_and_identity_matches=alive,
 remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')],modemmanager=mm,
 radio_boot_result=Path('/run/samurai-wifi/boot-finished').read_text().strip() if Path('/run/samurai-wifi/boot-finished').exists() else None)
private=dict(boot=boot,dmesg=subprocess.check_output(['dmesg']).decode(),qrtr=subprocess.check_output(['qrtr-lookup']).decode(),radio_log=Path('/run/samurai-wifi-boot.log').read_text() if Path('/run/samurai-wifi-boot.log').exists() else None,
 failure=(o/'failure-private.txt').read_text() if (o/'failure-private.txt').exists() else None,diag_events=(o/'diag-events-private.jsonl').read_text() if (o/'diag-events-private.jsonl').exists() else None)
print(json.dumps({'report':report,'private':private}))
