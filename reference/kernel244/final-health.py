from pathlib import Path
import dbus,hashlib,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();base=r/'k244-nextboot';state=json.loads((base/'capture/state-private.json').read_text());summary=json.loads((base/'capture/summary.json').read_text());assert state['terminal'] and state['exit_code']==0 and not Path('/proc',str(state['pid'])).exists()
stale=[]
for name in ['started','starting','stopping','inactive','failed','wasinactive']:
 p=Path('/run/openrc')/name/'samurai-diag244'
 if p.is_symlink():
  assert p.resolve()==Path('/etc/init.d/samurai-diag244');p.unlink();stale.append(name)
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text());nm=bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager');wlan=[]
for path in dbus.Interface(nm,'org.freedesktop.NetworkManager').GetDevices():
 p=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties');props=p.GetAll('org.freedesktop.NetworkManager.Device')
 if int(props['DeviceType'])==2:wlan.append(int(props['State']))
bus.close();qrtr=subprocess.check_output(['qrtr-lookup']).decode();local=[line for line in qrtr.splitlines() if len(line.split())>=5 and line.split()[0]=='4097' and line.split()[3]=='1'];dmesg=subprocess.check_output(['dmesg']).decode()
root_mount=next(line.split() for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]=='/')
report=dict(stage=244,current_guard='k244-runtime',new_linux_boot=True,kernel_version=os.uname().version,root_device=root_mount[0],root_fs=root_mount[2],taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')],
 mm_state=int(v['org.freedesktop.ModemManager1.Modem']['State']),mm_power=int(v['org.freedesktop.ModemManager1.Modem']['PowerState']),location_enabled=int(loc['Enabled']),signals_location=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 watch_running=watch['running'],assist_active=watch['active'],time_prepared=watch['time_prepared'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],wlan_states=wlan,
 diag_capture_terminal=True,diag_closed=summary['closed'],diag_mask_zero_reset_sent=summary['mask_zero_reset_sent'],diag_realtime_released=summary['diagnostic_mode_released'],local_diag_servers=len(local),
 boot_hook_absent=not Path('/etc/init.d/samurai-diag244').exists() and not Path('/etc/runlevels/default/samurai-diag244').exists(),stale_owned_openrc_entries_removed=stale,
 new_boot_fault_counts={k:dmesg.count(t) for k,t in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dsp_fatal='fatal error received').items()})
assert report['taint']==0 and not any(report['new_boot_fault_counts'].values()) and all(v['state']=='running' for v in report['remoteprocs']) and report['location_enabled']==0 and not report['assist_active'] and not local and report['boot_hook_absent'] and 100 in wlan
assert summary['mask_zero_reset_sent'] and summary['diagnostic_mode_released'] and summary['closed']
print(json.dumps({'report':report,'private':{'dmesg':dmesg,'qrtr':qrtr,'watch':watch,'diag_summary':summary,'module_notes':{p.parent.parent.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/sys/module').glob('*/notes/.note.gnu.build-id')}}}))
