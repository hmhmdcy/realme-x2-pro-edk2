from pathlib import Path
import dbus,hashlib,json,runpy,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-assist-final';assert not out.exists();out.mkdir(mode=0o700)
ns=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='assist_native_validation');old=(root/'k191-assistance/xtra-private.bin').read_bytes();digest=hashlib.sha256(old).hexdigest();assert digest=='e905a7291990c20324210b3bb405d84f8088da283f969255e2b28e34676d4008'
before=json.loads((root/'k201-validity-before/summary.json').read_text());rejected={digest:dict(start=before['start_utc_timestamp'],hours=before['duration_hours'])}
try:ns['validate_payload'](old,rejected,__import__('time').time())
except ValueError:old_rejected=True
else:raise AssertionError('Known expired actual payload accepted')
(root/'gnss-assist/rejected-payloads.json').write_text(json.dumps(rejected,indent=2)+'\n')
p=subprocess.run(['/usr/sbin/samurai-gnss-assist','--once'],capture_output=True,text=True,timeout=145);(out/'result-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0
worker=json.loads(p.stdout);assert worker['status']=='current' and worker['download_count']==worker['injection_count']==0 and worker['utc_ack_and_completion'] and worker['qmi_clients_released_and_closed'] and worker['modem_owner_unchanged']
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['source_sha256']==hashlib.sha256(Path('/usr/sbin/samurai-gnss-assist').read_bytes()).hexdigest() and watch['worker_starts']==0
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==3;bus.close()
r=dict(stage=201,source_sha256=watch['source_sha256'],actual_old191_payload_rejected_without_injection=old_rejected,native_utc_ack_and_indication=True,native_validity_current=True,all_qmi_clients_released_and_closed=True,no_data_download_or_reinjection=True,gps_enabled_final=0,power_state_unchanged=3,worker=worker)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
