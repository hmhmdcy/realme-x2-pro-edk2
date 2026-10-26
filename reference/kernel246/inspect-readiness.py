from pathlib import Path
import dbus,json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k246-runtime/boot-id-private.txt').read_bytes();s=json.loads((r/'k246-nextboot/capture/state-private.json').read_text());p=Path('/proc',str(s['pid']));alive=p.exists() and p.joinpath('stat').read_text().split()[21]==s['start_ticks'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text()) if (r/'gnss-assist/watch-state.json').exists() else None
bus=dbus.SystemBus(private=True);mm={}
if bus.name_has_owner('org.freedesktop.ModemManager1'):
 objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 for v in objects.values():
  if 'org.freedesktop.ModemManager1.Modem.Location' in v:mm=dict(state=int(v['org.freedesktop.ModemManager1.Modem']['State']),power=int(v['org.freedesktop.ModemManager1.Modem']['PowerState']),location_enabled=int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled']))
bus.close();radio=Path('/run/samurai-wifi/boot-finished');ready=alive and not s['terminal'] and s['state']=='ready' and bool(watch and watch['running'] and watch['time_prepared'] and watch['time_preparation_completions']>0 and not watch['active']) and mm.get('location_enabled')==0 and mm.get('power')==1
report=dict(stage=246,ready_for_baseline=ready,diag_worker_live=alive,diag_state=s,modemmanager=mm,watch_summary={k:watch.get(k) for k in ['running','active','time_prepared','worker_starts','worker_completions']} if watch else None,radio_boot_result=radio.read_text().strip() if radio.exists() else None,remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')])
print(json.dumps({'report':report,'private':dict(watch=watch)}))
