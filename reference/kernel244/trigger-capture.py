from pathlib import Path
import dbus,json,os,subprocess
r=Path('/var/lib/samurai');base=r/'k244-nextboot';o=base/'capture';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
s=json.loads((o/'state-private.json').read_text());p=Path('/proc')/str(s['pid']);assert not s['terminal'] and s['state']=='ready' and p.exists() and p.joinpath('stat').read_text().split()[21]==str(s['start_ticks'])
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and not watch['active']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0';(o/'before-session-dmesg-private.txt').write_bytes(subprocess.check_output(['dmesg']));(o/'before-session-watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
q=base/'capture90-request';assert not q.exists();q.write_bytes(b'capture90\n');bus.close()
print(json.dumps(dict(stage=244,new_boot_guard_pass=True,live_diag_pid_verified=True,one_capture_request_written=True,mm_power=int(v['org.freedesktop.ModemManager1.Modem']['PowerState']),time_prepared=watch['time_prepared'])))
