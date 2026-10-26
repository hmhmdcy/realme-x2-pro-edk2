from pathlib import Path
import hashlib
import host
import json

here = Path(__file__).resolve().parent
source = (here.parents[1] / 'linux-port/packages/samurai-gnss-assist/samurai-gnss-assist.py').read_bytes()
allowed = [hashlib.sha256(source).hexdigest(), hashlib.sha256(source.replace(b'\r\n', b'\n')).hexdigest()]
code = r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k226-baseline';out=root/'k226-assistance-refresh'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert not out.exists();out.mkdir(mode=0o700)
helper=Path('/usr/sbin/samurai-gnss-assist');digest=hashlib.sha256(helper.read_bytes()).hexdigest()
assert digest in ALLOWED
bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(base/'modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties')
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared']
(out/'watch-before-private.json').write_text(json.dumps(watch,indent=2)+'\n')
state=dict(state='starting',terminal=False,helper_source_verified=True,engine_start_sent=False,power_state_changed=False)
(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
with (out/'result-private.json').open('xb') as stdout,(out/'stderr-private.txt').open('xb') as stderr:
 process=subprocess.Popen(['/usr/bin/python3',str(helper),'--once'],stdout=stdout,stderr=stderr)
 state.update(state='running',pid=process.pid);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
 try:exit_code=process.wait(timeout=420)
 except subprocess.TimeoutExpired:
  state.update(state='observation-timeout-existing-worker-must-be-inspected');(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
  raise RuntimeError('Bounded helper observation expired; do not replay or kill an unresolved QMI operation')
state.update(state='terminal',terminal=True,exit_code=exit_code);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
result=json.loads((out/'result-private.json').read_text())
after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
afterwatch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-after-private.json').write_text(json.dumps(afterwatch,indent=2)+'\n')
report=dict(stage=226,helper_source_sha256=digest,status=result.get('status'),program_exit=exit_code,
 utc_ack_and_completion=result.get('utc_ack_and_completion'),download_count=result.get('download_count'),
 injection_count=result.get('injection_count'),validity_before_hours=result.get('validity_before',{}).get('hours'),
 validity_after_hours=result.get('hours'),qmi_clients_released_and_closed=result.get('qmi_clients_released_and_closed'),
 engine_start_sent=result.get('engine_start_sent'),power_state_changed=result.get('power_state_changed'),
 modem_owner_unchanged=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner,
 mm_location_properties_preserved=all(before[k]==after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),
 watcher_idle=not afterwatch['active'],watcher_worker_counts_preserved=all(watch[k]==afterwatch[k] for k in ['worker_starts','worker_completions']),
 payload_identifiers_server_addresses_and_validity_timestamps_private=True,
 no_nv_flash_reboot_or_dms_power_change=True)
bus.close();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert exit_code==0 and result['status'] in ['current','refreshed']
assert report['utc_ack_and_completion'] and report['qmi_clients_released_and_closed'] and not report['engine_start_sent'] and not report['power_state_changed']
assert report['modem_owner_unchanged'] and report['mm_location_properties_preserved'] and report['watcher_idle'] and report['watcher_worker_counts_preserved']
'''.replace('ALLOWED', repr(allowed))
state_path = host.PRIVATE / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='Existing verified helper one-shot UTC/validity/conditional refresh dispatched; no engine start',
             active_native_context='/var/lib/samurai/k226-assistance-refresh')
state_path.write_text(json.dumps(state, indent=2) + '\n')
run = host.ssh('python3 -', input=code.encode(), timeout=470)
(host.PRIVATE / 'assistance-refresh-host-private.log').write_bytes(run.stdout + run.stderr)
report = json.loads(run.stdout)
(here / 'assistance-refresh-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state.update(state='Verified helper one-shot terminal; inspect firmware validity before new capture',active_native_context=None)
state_path.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
