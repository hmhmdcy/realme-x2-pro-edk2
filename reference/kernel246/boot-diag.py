"""First-modem-startup logger; retain endpoints across two bounded sessions."""
from pathlib import Path
import collections,dbus,hashlib,json,os,signal,struct,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');base=r/'k246-nextboot';cfg=json.loads((base/'config-private.json').read_text());o=base/'capture';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=246,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);diag=None;child=None;failure=None;bus=None;props=None;modem=None;power_before=None;phases=[];versions=[];armed=False
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def stop(signum,frame):raise KeyboardInterrupt('First-startup diagnostic logger interrupted')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);save()
def log_counts(first=0):
 c=collections.Counter();bad=0
 for p in diag.received[first:]:
  if p and p[0]==0x10:
   if len(p)<16:bad+=1;continue
   a,b,code=struct.unpack_from('<HHH',p,2)
   if a!=b or b!=len(p)-4:bad+=1;continue
   c[hex(code)]+=1
 return dict(c),bad
def properties():
 global bus,props,modem
 if bus is None:
  bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path=next(str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v);obj=bus.get_object(owner,path);props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');modem=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem')
 loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and not watch['active'] and watch['time_prepared'] and not bus.name_has_owner('org.freedesktop.GeoClue2')
 return loc,watch,int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))
def verify_file_services(label):
 for name,expected in [('rmtfs','d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'),('tftp','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')]:
  pid=int(Path('/run/samurai-wifi',name+'.pid').read_text());p=Path('/proc',str(pid));assert hashlib.sha256((p/'exe').read_bytes()).hexdigest()==expected
  if name=='tftp':assert b'SAMURAI_TFTP_RW_ROOT=/run/samurai-wifi/tftp-rw' in (p/'environ').read_bytes().split(b'\0')
 x=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/(label+'-nv-source-private.txt')).write_bytes(x.stdout+x.stderr);assert x.returncode==0
def phase(label):
 global child,power_before
 loc,watch,power=properties();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0';verify_file_services(label+'-before')
 if power_before is None:power_before=power
 (o/(label+'-watch-before-private.json')).write_text(json.dumps(watch,indent=2)+'\n');before=subprocess.check_output(['dmesg']);(o/(label+'-dmesg-before-private.txt')).write_bytes(before);start=time.monotonic();first=len(diag.received);state.update(state='gnss_running',phase=label);save()
 with (o/(label+'-loc-events-private.jsonl')).open('xb') as out,(o/(label+'-loc-stderr-private.txt')).open('xb') as err:
  binary=r/'k226-loc-tools-r3/loc-session';assert hashlib.sha256(binary.read_bytes()).hexdigest()==cfg['loc_binary_sha256'];env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None);child=subprocess.Popen([str(binary),'high'],stdout=out,stderr=err,env=env);state['child_pid']=child.pid;save();last=0
  try:
   while child.poll() is None:
    if time.monotonic()-start>170:raise RuntimeError('Bounded LOC deadline')
    diag.poll(0.25)
    if time.monotonic()-last>3:
     c,bad=log_counts();state.update(diag_log_counts=c,invalid_log_lengths=bad,diag_decode_errors=diag.decode_errors,elapsed_seconds=round(time.monotonic()-began));save();last=time.monotonic()
  finally:
   if child.poll() is None:child.terminate();child.wait(timeout=40)
 rows=[json.loads(x) for x in (o/(label+'-loc-events-private.jsonl')).read_text().splitlines()];cleanup=rows[-1];assert child.returncode==0 and cleanup['kind']=='cleanup' and all(cleanup[k] for k in ['stop_ack','client_released','device_closed']);decoded=summarize(rows);assert not decoded['decode_errors'];after=subprocess.check_output(['dmesg']);(o/(label+'-dmesg-after-private.txt')).write_bytes(after);loc_after,watch_after,power_after=properties();verify_file_services(label+'-after');c,bad=log_counts(first)
 result=dict(label=label,receiver=decoded,diag_log_counts=c,invalid_log_lengths=bad,cleanup=cleanup,time_prepared_before=True,mm_power=power,location_preserved=all(loc[k]==loc_after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),power_preserved=power==power_after,watch_preserved=all(watch[k]==watch_after[k] for k in ['worker_starts','worker_completions']),fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},elapsed_seconds=round(time.monotonic()-start,2));assert not bad and result['location_preserved'] and result['power_preserved'] and result['watch_preserved'] and not any(result['fault_delta'].values());phases.append(result);(o/(label+'-summary.json')).write_text(json.dumps(result,indent=2)+'\n');state.update(state='ready',phases_completed=[x['label'] for x in phases],diag_log_counts=log_counts()[0]);save()
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot!=cfg['previous_boot'] and Path('/proc/device-tree/model').read_bytes().hex()==cfg['model_hex'] and os.uname().release==cfg['kernel_release']
 runtime=r/'k246-runtime';assert not runtime.exists();runtime.mkdir(mode=0o700);(runtime/'boot-id-private.txt').write_text(boot+'\n');(o/'boot-id-private.txt').write_text(boot+'\n');(o/'dmesg-before-private.txt').write_bytes(subprocess.check_output(['dmesg']))
 sys.path.insert(0,str(base));from diag_streaming import Diag,regression;from loc_decode import summarize
 regression();began=time.monotonic();queried=False
 with (o/'diag-events-private.jsonl').open('x') as log:
  diag=Diag(log)
  try:
   Path('/run/samurai-diag246-ready').write_text('published\n');state.update(state='published_before_modem');save();last=0
   while time.monotonic()-began<1200:
    diag.poll(0.25)
    if diag.sent_features and diag.remote_cmd and len(diag.diag_ids)==2 and not queried:
     queried=True
     for i in range(2):
      p=diag.query(b'\0',seconds=3);versions.append(dict(present=p is not None,code=p[0] if p else None,bytes=len(p) if p else 0))
     # Match the proven244 first-startup order; stream17 is NOT newly added.
     diag.diagnostic_mode(True);diag.gnss_logs(True);armed=True;state.update(state='ready',versions=versions,diag_ids=len(diag.diag_ids),phases_completed=[]);save()
    if (base/'stop-request').exists():assert (base/'stop-request').read_bytes()==b'stop\n';break
    if (base/'baseline90-request').exists() and not phases:
     assert armed and (base/'baseline90-request').read_bytes()==b'baseline90\n';phase('baseline-off')
    if (base/'online90-request').exists() and len(phases)==1:
     assert armed and (base/'online90-request').read_bytes()==b'online90\n';properties();assert power_before==1;modem.SetPowerState(dbus.UInt32(3),timeout=30);assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==3
     try:phase('comparison-online')
     finally:modem.SetPowerState(dbus.UInt32(power_before),timeout=30);assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power_before;state['power_restored']=True;save()
    if time.monotonic()-last>3:
     c,bad=log_counts();state.update(diag_log_counts=c,invalid_log_lengths=bad,diag_decode_errors=diag.decode_errors,elapsed_seconds=round(time.monotonic()-began));save();last=time.monotonic()
  finally:
   try:
    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   finally:diag.close()
 if props is not None and power_before is not None:assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power_before
 c,bad=log_counts();report=dict(stage=246,first_startup_fresh_feature=queried,versions=versions,diag_ids=len(diag.diag_ids),phases=phases,log_counts=c,invalid_log_lengths=bad,decode_errors=diag.decode_errors,diag_rx_records=diag.records,diag_rx_bytes=diag.bytes,logging_armed=armed,streaming_control17_sent=diag.streaming_sent,mask_zero_reset_request_sent=diag.log_mask_reset_sent,realtime_release_request_sent=not diag.mode_enabled,closed=diag.closed,elapsed_seconds=round(time.monotonic()-began,2))
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert not bad and not diag.decode_errors;state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 failure=traceback.format_exc();(o/'failure-private.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
  if diag and not diag.closed:diag.close()
  if props is not None and power_before is not None and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))!=power_before:modem.SetPowerState(dbus.UInt32(power_before),timeout=30)
 except BaseException:(o/'cleanup-failure-private.txt').write_text(traceback.format_exc());failure=failure or 'cleanup failure'
 if bus:bus.close()
 (o/'dmesg-after-private.txt').write_bytes(subprocess.check_output(['dmesg']))
 if failure:state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1,diag_closed=bool(diag and diag.closed));save()
if failure:raise SystemExit(1)
