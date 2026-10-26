"""One bounded GNSS session, with temporary GNSS-only diagnostic logging."""
from pathlib import Path
import dbus,hashlib,json,os,struct,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k243-gnss-diag';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=243,state='preflight',terminal=False,pid=os.getpid())
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
save();instance=Path('/sys/kernel/tracing/instances/gnss243');owned=False;child=None;bus=None;diag=None;error=None
def snap(label):
 data={name:Path(path).read_text() for name,path in dict(clk='/sys/kernel/debug/clk/clk_summary',regulator='/sys/kernel/debug/regulator/regulator_summary',gpio='/sys/kernel/debug/gpio',genpd='/sys/kernel/debug/pm_genpd/pm_genpd_summary').items()}
 data['monotonic_ns']=time.monotonic_ns();(o/(label+'-private.json')).write_text(json.dumps(data,indent=2)+'\n')
def service_logs(label):
 for name in ['tftp','rmtfs']:
  p=Path('/run/samurai-wifi')/(name+'.log')
  if p.is_file():
   assert p.stat().st_size<32*1024*1024
   (o/(label+'-'+name+'-private.log')).write_bytes(p.read_bytes())
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(r/'k236-runtime/boot-id-private.txt').read_bytes()
 tools=r/'k226-loc-tools-r3';b=tools/'loc-session';build=json.loads((tools/'build-summary.json').read_text());assert hashlib.sha256(b.read_bytes()).hexdigest()==build['binary_sha256']
 assert build['message_allowlist']==[33,34,35,50,51,63,75] and build['fixed_observation_seconds']==90
 sys.path.insert(0,str(r/'k243-diag-python-r3'));from diag_transport import Diag,regression
 regression();bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
 objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();paths=[str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
 props=dbus.Interface(bus.get_object(owner,paths[0]),'org.freedesktop.DBus.Properties');beforeprops=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert not watch['active'] and int(beforeprops['Enabled'])==0 and not beforeprops['SignalsLocation']
 assert not bus.name_has_owner('org.freedesktop.GeoClue2') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 db=Path('/lib/apk/db/installed').read_bytes();before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before)
 assert not instance.exists();instance.mkdir();owned=True
 (instance/'tracing_on').write_text('0');(instance/'buffer_size_kb').write_text('1024');(instance/'trace_clock').write_text('mono')
 enabled=[]
 for group in ['clk','regulator']:
  for event in (instance/'events'/group).iterdir():
   if not (event/'format').is_file():continue
   if group=='clk':
    if 'char[] name;' not in (event/'format').read_text():continue
    names=['bi_tcxo','bi_tcxo_ao','rf_clk1','rf_clk1_ao','rf_clk2','rf_clk2_ao','rf_clk3','rf_clk3_ao','xo_board','gcc_mss_mfab_axis_clk','gcc_mss_cfg_ahb_clk']
    (event/'filter').write_text(' || '.join('name == "'+n+'"' for n in names))
   (event/'enable').write_text('1');enabled.append(group+'/'+event.name)
 snap('before');service_logs('before');(instance/'tracing_on').write_text('1');(instance/'trace_marker').write_text('gnss243-before-diagnostic-transport\n')
 observed=[json.loads(x) for x in (r/'k243-diag-passive-r3/events-private.jsonl').read_text().splitlines()]
 feature=next(x for x in observed if x.get('channel')=='control' and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8));raw=bytes.fromhex(feature['hex']);width=struct.unpack_from('<I',raw,8)[0];assert len(raw)==12+width
 with (o/'diag-events-private.jsonl').open('x') as diagout,(o/'events-private.jsonl').open('xb') as locout,(o/'stderr-private.txt').open('xb') as errout:
  diag=Diag(diagout,((feature['node'],feature['port']),int.from_bytes(raw[12:],'little'),width))
  try:
   diag.prepare();reply=diag.query(b'\x00');assert reply and reply[0]==0
   diag.gnss_logs(True);(instance/'trace_marker').write_text('gnss243-before-loc-start\n')
   env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None);start=time.monotonic()
   child=subprocess.Popen([str(b),'high'],stdout=locout,stderr=errout,env=env);state.update(state='running',child_pid=child.pid);save();samples=set()
   while child.poll() is None:
    if time.monotonic()-start>165:raise RuntimeError('LOC total deadline')
    diag.poll(0.5)
    for t in [5,30,75]:
     if t not in samples and time.monotonic()-start>=t:snap('active-'+str(t));samples.add(t)
  finally:
   try:
    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   finally:diag.close()
  rc=child.returncode
 snap('after');service_logs('after');(instance/'trace_marker').write_text('gnss243-after-stop-and-diag-close\n');(instance/'tracing_on').write_text('0')
 (o/'trace-private.txt').write_text((instance/'trace').read_text());stats={p.parent.name:p.read_text() for p in (instance/'per_cpu').glob('cpu*/stats')};(o/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
 records=[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()];closed=records[-1];assert closed['kind']=='cleanup'
 logs={}
 for packet in diag.received:
  if len(packet)>=16 and packet[0]==0x10:
   code=struct.unpack_from('<H',packet,6)[0];logs[str(code)]=logs.get(str(code),0)+1
 afterprops=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');afterwatch=json.loads((r/'gnss-assist/watch-state.json').read_text());after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after)
 report=dict(stage=243,program_exit=rc,cleanup=closed,environment='indoor window opened; other phones receive GPS per user',
  diag_log_counts=logs,diag_decode_errors=diag.decode_errors,diag_received_packets=diag.records,diag_received_bytes=diag.bytes,
  diag_mask_zero_reset_sent=diag.log_mask_reset_sent,previous_mask_not_readable_and_exact_restoration_not_claimed=True,diag_transport_closed=diag.closed,
  no_diag_mode_sleep_vote_or_rf_nv_changes=True,enabled_trace_events=len(enabled),samples_taken=sorted(samples),
  no_trace_overrun=all('overrun: 0\n' in v and 'dropped events: 0\n' in v for v in stats.values()),
  mm_preserved=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner and all(beforeprops[k]==afterprops[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),
  assist_preserved=not afterwatch['active'] and all(watch[k]==afterwatch[k] for k in ['worker_starts','worker_completions']),package_database_preserved=db==Path('/lib/apk/db/installed').read_bytes(),
  fault_delta={k:after.count(s)-before.count(s) for k,s in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 assert rc==0 and all(closed[k] for k in ['stop_ack','client_released','device_closed']) and report['mm_preserved'] and report['assist_preserved'] and report['package_database_preserved']
 assert report['no_trace_overrun'] and report['taint']==0 and not any(report['fault_delta'].values()) and report['diag_mask_zero_reset_sent']
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(o/'failure-private.txt').write_text(error);state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1);save()
finally:
 if diag and not diag.closed:diag.close()
 if owned:
  (instance/'tracing_on').write_text('0');(instance/'events/enable').write_text('0');instance.rmdir();state['trace_instance_removed']=True;save()
 if bus:bus.close()
if error:raise SystemExit(1)
