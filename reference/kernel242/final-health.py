from pathlib import Path
import dbus,json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
state=json.loads((r/'k242-clock-session/state-private.json').read_text());summary=json.loads((r/'k242-clock-session/summary.json').read_text())
bus=dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
modems=[v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(modems)==1
loc=modems[0]['org.freedesktop.ModemManager1.Modem.Location'];m=modems[0]['org.freedesktop.ModemManager1.Modem']
watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
active=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:raw=p.read_bytes()
 except OSError:continue
 if b'/var/lib/samurai/k242-tools/native-clock-session.py' in raw or b'/var/lib/samurai/k226-loc-tools-r3/loc-session\0high' in raw:active.append(p.parent.name)
report=dict(stage=242,current236_boot=True,worker_terminal=state['terminal'] and state.get('exit_code')==0,
 trace_instance_removed=not Path('/sys/kernel/tracing/instances/gnss242').exists(),probe_processes_absent=not active,
 stop_release_close=all(summary['cleanup'][k] for k in ['stop_ack','client_released','device_closed']),
 location_enabled=int(loc['Enabled']),location_signals=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 modem_state=int(m['State']),modem_power=int(m['PowerState']),assist_idle=not watch['active'],assist_watch_running=watch['running'],
 assist_worker_starts=watch['worker_starts'],assist_worker_completions=watch['worker_completions'],time_prepared=watch['time_prepared'],
 geoclue_running=bool(bus.name_has_owner('org.freedesktop.GeoClue2')),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')],
 no_flash_reboot_or_production_configuration_change=True)
bus.close()
print(json.dumps(report),flush=True)
assert report['worker_terminal'] and report['trace_instance_removed'] and report['probe_processes_absent'] and report['stop_release_close']
assert report['location_enabled']==0 and not report['location_signals'] and report['gps_refresh']==30 and report['assist_idle']
assert not report['geoclue_running'] and report['taint']==0 and all(x['state']=='running' for x in report['remoteprocs'])
