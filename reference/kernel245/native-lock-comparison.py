"""Bounded MT/NONE comparison using the standard LOC API and original NV COW."""
from pathlib import Path
import dbus,hashlib,json,os,signal,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k245-engine-lock';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=245,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);bus=None;child=None;changed=False;error=None;phases=[];restored=False
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def interrupt(signum,frame):raise KeyboardInterrupt('Lock comparison interrupted')
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt);save()
def qmi(option,label):
 x=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=15);(o/(label+'-qmi-private.txt')).write_bytes(x.stdout+x.stderr);assert x.returncode==0
 return x.stdout.decode().strip()
def lock(label):
 text=qmi('--loc-get-engine-lock',label);prefix='Successfully retrieved engine lock: ';assert text.startswith(prefix);value=text[len(prefix):];assert value in ['none','mi','mt','all'];return value
def phase(label):
 global child
 state.update(state='running',phase=label);save();start=time.monotonic()
 with (o/(label+'-events-private.jsonl')).open('xb') as out,(o/(label+'-stderr-private.txt')).open('xb') as err:
  env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None);child=subprocess.Popen([str(binary),'high'],stdout=out,stderr=err,env=env);state['child_pid']=child.pid;save()
  try:
   while child.poll() is None:
    if time.monotonic()-start>170:raise RuntimeError('LOC bounded deadline')
    time.sleep(0.5)
  finally:
   if child.poll() is None:child.terminate();child.wait(timeout=40)
 rows=[json.loads(x) for x in (o/(label+'-events-private.jsonl')).read_text().splitlines()];cleanup=rows[-1];assert child.returncode==0 and cleanup['kind']=='cleanup' and all(cleanup[k] for k in ['stop_ack','client_released','device_closed'])
 decoded=summarize(rows);assert not decoded['decode_errors'];positive=decoded['sv'].get('positive_snr',0)>0 or decoded['sv'].get('valid_track',0)>0 or decoded['position_status_counts'].get('0',0)>0
 result=dict(label=label,receiver=decoded,cleanup=cleanup,positive_reception_or_position_candidate=positive,elapsed_seconds=round(time.monotonic()-start,2));phases.append(result);(o/(label+'-summary.json')).write_text(json.dumps(result,indent=2)+'\n');state['phases_completed']=[x['label'] for x in phases];save();return positive
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 pid=int(Path('/run/samurai-wifi/rmtfs.pid').read_text());assert hashlib.sha256(Path('/proc',str(pid),'exe').read_bytes()).hexdigest()=='d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'
 check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-source-before-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path=next(str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v);props=dbus.Interface(bus.get_object(owner,path),'org.freedesktop.DBus.Properties');loc_before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');power_before=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))
 watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(loc_before['Enabled'])==0 and not loc_before['SignalsLocation'] and not watch['active'] and watch['time_prepared'] and not bus.name_has_owner('org.freedesktop.GeoClue2')
 assert lock('initial-lock')=='mt';db=Path('/lib/apk/db/installed').read_bytes();before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before)
 tools=r/'k226-loc-tools-r3';binary=tools/'loc-session';build=json.loads((tools/'build-summary.json').read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256'] and build['fixed_observation_seconds']==90 and build['message_allowlist']==[33,34,35,50,51,63,75]
 sys.path.insert(0,str(r/'k245-tools'));from loc_decode import summarize
 if not phase('baseline-mt'):
  state.update(state='setting_none');save();changed=True;qmi('--loc-set-engine-lock=none','set-none');assert lock('read-none')=='none'
  positive=phase('test-none');assert lock('post-none')=='none'
  qmi('--loc-set-engine-lock=mt','restore-mt');assert lock('read-restored-mt')=='mt';restored=True;changed=False
  if positive:phase('confirmation-mt')
 else:restored=True
 after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after);watch_after=json.loads((r/'gnss-assist/watch-state.json').read_text());loc_after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-source-after-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 report=dict(stage=245,phases=phases,engine_lock_restored=lock('final-lock')=='mt',none_tested=any(x['label']=='test-none' for x in phases),normal_engine_lock_api_only=True,original_nv_sources_preserved=True,
  time_prepared_before_sessions=True,location_preserved=all(loc_before[k]==loc_after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),mm_power_preserved=power_before==int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState')),watch_preserved=not watch_after['active'] and all(watch[k]==watch_after[k] for k in ['worker_starts','worker_completions']),package_db_preserved=db==Path('/lib/apk/db/installed').read_bytes(),
  fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert report['engine_lock_restored'] and report['location_preserved'] and report['mm_power_preserved'] and report['watch_preserved'] and report['package_db_preserved'] and report['taint']==0 and not any(report['fault_delta'].values())
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
finally:
 try:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
 finally:
  if changed:
   try:
    current=lock('failure-read-lock');assert current in ['none','mt']
    if current=='none':qmi('--loc-set-engine-lock=mt','failure-restore-mt')
    restored=lock('failure-confirm-mt')=='mt'
   except BaseException:(o/'restore-failure-private.txt').write_text(traceback.format_exc())
  if bus:bus.close()
 if error:state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1,restored_to_mt=restored);save()
if error:raise SystemExit(1)
