from pathlib import Path
import base64
import host
import json
import sys

here = Path(__file__).resolve().parent
assert len(sys.argv) in [2, 3] and sys.argv[1] in ['probe', 'default', 'high']
kind = sys.argv[1]
label = sys.argv[2] if len(sys.argv) == 3 else None
assert label is None or (label == 'aided' and kind in ['default', 'high'])
case = kind + ('-' + label if label else '')
build = json.loads((here / 'loc-session-r3-build-validation.json').read_text())
decoder = base64.b64encode((here / 'loc_decode.py').read_bytes()).decode()
code = r'''
from pathlib import Path
import base64,dbus,hashlib,json,os,subprocess,sys,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k226-baseline';kind=KIND;case=CASE;aided=AIDED
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
out=root/('k226-loc-r3-'+case);assert not out.exists();out.mkdir(mode=0o700)
if aided:
 preparation=json.loads((root/'k226-assistance-refresh/summary.json').read_text())
 assert preparation['status']=='refreshed' and preparation['validity_after_hours']==168 and preparation['qmi_clients_released_and_closed']
tools=root/'k226-loc-tools-r3';binary=tools/'loc-session';assert hashlib.sha256(binary.read_bytes()).hexdigest()==BINARY_SHA
source=tools/'loc_decode.py';payload=base64.b64decode(DECODER)
if source.exists():assert source.read_bytes()==payload
else:source.write_bytes(payload)
sys.path.insert(0,str(tools));from loc_decode import summarize,regression
parser_proof=regression()
bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(base/'modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties')
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0 and not before['SignalsLocation']
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active']
(out/'watch-before-private.json').write_text(json.dumps(watch,indent=2)+'\n')
db=Path('/lib/apk/db/installed').read_bytes();dmesg=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(dmesg)
state=dict(kind=kind,state='starting',terminal=False,boot_matches=True,engine_start_possible=kind!='probe')
(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
with (out/'events-private.jsonl').open('xb') as stdout,(out/'stderr-private.txt').open('xb') as stderr:
 process=subprocess.Popen([str(binary),kind],stdout=stdout,stderr=stderr,env=env)
 state.update(state='running',pid=process.pid);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
 try:exit_code=process.wait(timeout=250)
 except subprocess.TimeoutExpired:
  state.update(state='termination-requested');(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n');process.terminate()
  try:exit_code=process.wait(timeout=45)
  except subprocess.TimeoutExpired:
   state.update(state='cleanup-unresolved',terminal=False);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n');raise RuntimeError('Existing LOC operation requires inspection; do not replay')
records=[json.loads(line) for line in (out/'events-private.jsonl').read_text().splitlines()]
closed=records[-1];assert closed['kind']=='cleanup'
state.update(state='terminal',terminal=True,exit_code=exit_code,cleanup=closed)
(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
report=summarize(records);report.update(stage=226,kind=kind,case=case,program_exit=exit_code,cleanup=closed,parser_regression=parser_proof,
 source_sha256=SOURCE_SHA,binary_sha256=BINARY_SHA,decoder_sha256=hashlib.sha256(payload).hexdigest(),
 coordinates_and_identifiers_retained_only_in_private_raw_logs=True,no_nv_or_rf_configuration_write=True,
 temporary_start_session_only=kind!='probe',aiding_data_inherited_not_reinjected=True,
 no_claim_of_fresh_aiding_validity=not aided,aiding_refreshed_and_current_before_this_capture=aided,
 observation_seconds_requested=0 if kind=='probe' else 90)
after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
report['mm_owner_and_location_properties_preserved']=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner and all(before[k]==after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate'])
afterwatch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-after-private.json').write_text(json.dumps(afterwatch,indent=2)+'\n')
report['watch_idle_and_worker_counts_preserved']=not afterwatch['active'] and all(watch[k]==afterwatch[k] for k in ['worker_starts','worker_completions'])
afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
report['fault_delta']={k:afterlog.count(v)-dmesg.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report['taint']=int(Path('/proc/sys/kernel/tainted').read_text())
report['package_database_preserved']=Path('/lib/apk/db/installed').read_bytes()==db
report['same_boot']=Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
bus.close();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert exit_code==0 and closed['client_released'] and closed['device_closed'] and not closed['interrupted']
assert report['mm_owner_and_location_properties_preserved'] and report['watch_idle_and_worker_counts_preserved']
assert report['same_boot'] and report['package_database_preserved'] and report['taint']==0 and not any(report['fault_delta'].values())
assert not report['decode_errors']
if kind!='probe':assert closed['start_ack'] and closed['stop_ack'] and report['engine_states'][-1:]==[2]
'''
values = {'KIND': kind, 'CASE': case, 'AIDED': bool(label), 'BINARY_SHA': build['binary_sha256'], 'SOURCE_SHA': build['source_sha256'], 'DECODER': decoder}
import re
code = re.sub(r'\b(KIND|CASE|AIDED|BINARY_SHA|SOURCE_SHA|DECODER)\b', lambda m: repr(values[m[0]]), code)
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='LOC r3 '+case+' operation dispatched; follow this exact operation to terminal',active_native_context='/var/lib/samurai/k226-loc-r3-'+case)
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
run = host.ssh('python3 -', input=code.encode(), timeout=325)
(host.PRIVATE / ('loc-r3-'+case+'-host-private.log')).write_bytes(run.stdout + run.stderr)
report = json.loads(run.stdout)
(here / ('loc-r3-'+case+'-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
state.update(state='LOC '+case+' operation terminal and cleanup verified',active_native_context=None)
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
