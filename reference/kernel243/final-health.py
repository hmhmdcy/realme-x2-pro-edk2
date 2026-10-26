from pathlib import Path
import dbus,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
qrtr=subprocess.check_output(['qrtr-lookup']).decode();local=[]
for line in qrtr.splitlines():
 f=line.split()
 if len(f)>=5 and f[0]=='4097' and f[3]=='1':local.append(f[:5])
active=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:argv=p.read_bytes().split(b'\0')
 except OSError:continue
 if argv and argv[0].endswith(b'/loc-session'):active.append(int(p.parent.name))
states={n:json.loads((r/n/'state-private.json').read_text()) for n in ['k243-gnss-diag','k243-window-clock','k243-wlan-control','k243-wlan-off-clock']}
report=dict(stage=243,same236_boot=True,location_enabled=int(loc['Enabled']),location_signals=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 watch_running=watch['running'],assist_active=watch['active'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],time_prepared=watch['time_prepared'],
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')],
 active_loc_processes=len(active),local_diag_servers_remaining=len(local),all_workers_terminal=all(x['terminal'] for x in states.values()),
 trace_instances_removed=all(not Path('/sys/kernel/tracing/instances',n).exists() for n in ['gnss243','gnss243window','gnss243ldo','gnss243wlan']),no_flash_or_reboot=True,no_diag_gnss_log_mask_sent=True)
nm=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
report['wlan_enabled']=bool(nm.Get('org.freedesktop.NetworkManager','WirelessEnabled'));report['wlan_softblocked']=any((p/'type').read_text().strip()=='wlan' and (p/'soft').read_text().strip()!='0' for p in Path('/sys/class/rfkill').glob('rfkill*'))
wireless=[]
for path in dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.NetworkManager').GetDevices():
 p=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties');device=p.GetAll('org.freedesktop.NetworkManager.Device')
 if int(device['DeviceType'])==2:wireless.append(int(device['State']))
report['wlan_device_states']=wireless
assert report['location_enabled']==0 and not report['location_signals'] and not report['assist_active'] and not active and not local and report['taint']==0 and report['trace_instances_removed']
assert report['wlan_enabled'] and not report['wlan_softblocked'] and 100 in wireless
bus.close();print(json.dumps({'report':report,'private':{'qrtr':qrtr,'dmesg':subprocess.check_output(['dmesg']).decode(),'states':states}}))
