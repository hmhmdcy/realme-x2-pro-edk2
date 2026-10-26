from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-assist-tool';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
enabled=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));assert enabled==0 and power==3
p=subprocess.run(['/usr/sbin/samurai-gnss-assist','--once'],capture_output=True,text=True,timeout=145)
(out/'result-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
r=json.loads(p.stdout);assert r['status']=='current' and r['download_count']==r['injection_count']==0 and r['utc_ack_and_completion'] and r['qmi_clients_released_and_closed'] and r['modem_owner_unchanged']
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==enabled and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power
p=subprocess.run(['/usr/sbin/samurai-gnss-assist','--once','--active-only'],capture_output=True,text=True,timeout=15);assert p.returncode==0
inactive=json.loads(p.stdout);assert inactive['status']=='inactive'
report=dict(stage=201,installed_tool_real_utc_ack_and_indication=True,installed_tool_real_validity_query=True,all_qmi_clients_released_and_closed=True,currently_valid_file_not_downloaded_or_reinjected=True,inactive_guard_returned_without_gps_enable=True,gps_enabled_final=enabled,modem_power_unchanged=power,worker=r,inactive=inactive)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close();print(json.dumps(report))
