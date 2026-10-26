"""Same-boot cached DIAG resume, followed by bounded GNSS/RF observations.

No new feature exchange is claimed. The old AP ports and VERSION payload must
match the still-running modem before sending diagnostic masks and mode requests.
The only optional second action is standard MM SetPowerState(ON), then GNSS.
"""
from pathlib import Path
import collections,dbus,hashlib,json,os,re,signal,struct,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k245-resume-rf-r4';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=245,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);d=None;child=None;bus=None;failure=None;phases=[];power_before=None;props=None;closed=False
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def stop(signum,frame):raise KeyboardInterrupt('Diagnostic capture stopped')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);save()
def qmi(option):
 x=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=15);assert x.returncode==0;return x.stdout.decode().strip()
def counts():
 c=collections.Counter();bad=0
 for p in d.received:
  if p and p[0]==0x10:
   if len(p)<16:bad+=1;continue
   a,b,code=struct.unpack_from('<HHH',p,2)
   if a!=b or b!=len(p)-4:bad+=1;continue
   c[hex(code)]+=1
 return dict(c),bad
def run_phase(label):
 global child
 assert time.monotonic()-began<800
 watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert watch['time_prepared'] and not watch['active']
 state.update(state='gnss_running',phase=label);save();start=time.monotonic();before=len(d.received)
 with (o/(label+'-events-private.jsonl')).open('xb') as out,(o/(label+'-stderr-private.txt')).open('xb') as err:
  env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None);child=subprocess.Popen([str(binary),'high'],stdout=out,stderr=err,env=env);state['child_pid']=child.pid;save();last=0
  try:
   while child.poll() is None:
    if time.monotonic()-start>170:raise RuntimeError('Bounded GNSS deadline')
    d.poll(0.25)
    if time.monotonic()-last>3:
     c,bad=counts();state.update(diag_log_counts=c,invalid_log_lengths=bad,diag_decode_errors=d.decode_errors,elapsed_seconds=round(time.monotonic()-began));save();last=time.monotonic()
  finally:
   if child.poll() is None:child.terminate();child.wait(timeout=40)
 rows=[json.loads(x) for x in (o/(label+'-events-private.jsonl')).read_text().splitlines()];cleanup=rows[-1];assert child.returncode==0 and cleanup['kind']=='cleanup' and all(cleanup[k] for k in ['stop_ack','client_released','device_closed'])
 decoded=summarize(rows);assert not decoded['decode_errors'];c,bad=counts()
 result=dict(label=label,receiver=decoded,cleanup=cleanup,diag_payloads_added=len(d.received)-before,diag_log_counts_cumulative=c,invalid_log_lengths=bad,elapsed_seconds=round(time.monotonic()-start,2));phases.append(result)
 (o/(label+'-summary.json')).write_text(json.dumps(result,indent=2)+'\n');state.update(state='waiting',phases_completed=[x['label'] for x in phases],diag_log_counts=c);save()
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(r/'k244-runtime/boot-id-private.txt').read_bytes()==(r/'k244-nextboot/capture/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 oldstate=json.loads((r/'k244-nextboot/capture/state-private.json').read_text());assert oldstate['terminal'] and oldstate['exit_code']==0
 for name,expected in [('rmtfs','d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'),('tftp','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')]:
  pid=int(Path('/run/samurai-wifi',name+'.pid').read_text());p=Path('/proc',str(pid));assert hashlib.sha256((p/'exe').read_bytes()).hexdigest()==expected
  if name=='tftp':assert b'SAMURAI_TFTP_RW_ROOT=/run/samurai-wifi/tftp-rw' in (p/'environ').read_bytes().split(b'\0')
 check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-before-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 before_dmesg=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before_dmesg);assert sum(b'Booting fw image' in x and b'/modem.mdt' in x for x in before_dmesg.splitlines())==1
 pkg=Path('/lib/apk/db/installed').read_bytes();bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path=next(str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v);props=dbus.Interface(bus.get_object(owner,path),'org.freedesktop.DBus.Properties');modem=dbus.Interface(bus.get_object(owner,path),'org.freedesktop.ModemManager1.Modem')
 loc_before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');power_before=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));assert power_before==1 and int(loc_before['Enabled'])==0 and not loc_before['SignalsLocation'] and not bus.name_has_owner('org.freedesktop.GeoClue2')
 watch_before=json.loads((r/'gnss-assist/watch-state.json').read_text());assert not watch_before['active'] and watch_before['time_prepared'];assert qmi('--loc-get-engine-lock')=='Successfully retrieved engine lock: mt'
 tools=r/'k226-loc-tools-r3';binary=tools/'loc-session';build=json.loads((tools/'build-summary.json').read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256'] and build['fixed_observation_seconds']==90 and build['message_allowlist']==[33,34,35,50,51,63,75]
 sys.path.insert(0,str(r/'k245-tools'));from diag_resume_rf import Diag,frames,regression;from loc_decode import summarize
 regression();seed=(r/'k244-nextboot/capture/diag-events-private.jsonl').read_bytes();old=[json.loads(x) for x in seed.splitlines()];ports=next(x['ports'] for x in old if x['kind']=='local_endpoints');feature=next(x for x in old if x['kind']=='feature_negotiation');old_versions={p for x in old if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe for p in frames(bytes.fromhex(x['hex'])) if p and p[0]==0};assert old_versions and all(len(p)==55 and p[0]==0 for p in old_versions)
 peer=None;ids={};deleted=[]
 for x in old:
  if x['kind']!='rx':continue
  b=bytes.fromhex(x['hex'])
  if x['port']==0xfffffffe and len(b)==20 and struct.unpack_from('<I',b)[0]==6:deleted.append(struct.unpack_from('<II',b,4))
  if x['channel']!=0 or x['node']!=0 or x['port']==0xfffffffe:continue
  off=0
  while off+8<=len(b):
   cmd,n=struct.unpack_from('<II',b,off);body=b[off+8:off+8+n];assert len(body)==n
   if cmd==8:peer=(x['node'],x['port'])
   if cmd==33:
    ver,proposed=struct.unpack_from('<II',body);name=body[8:];assert ver==1 and name.endswith(b'\0')
    if name not in ids:ids[name]=len(ids)+2
   off+=8+n
  assert off==len(b)
 assert peer and peer not in deleted and len(ids)==2
 for name in ['rmtfs','tftp']:
  text=Path('/run/samurai-wifi',name+'.log').read_text(errors='replace');assert not re.search(r'\bdel_client(?: for)?\s+'+str(peer[0])+':'+str(peer[1])+r'\b',text)
 began=time.monotonic()
 with (o/'diag-events-private.jsonl').open('x') as log:
  d=Diag(log,fixed_ports=ports)
  try:
   end=time.monotonic()+4
   while time.monotonic()<end:d.poll(min(0.25,end-time.monotonic()))
   assert d.remote_cmd and peer not in d.deleted_peers and not d.sent_features,'Cached path requires no new feature exchange'
   first_version=len(d.received)
   for i in range(2):
    first=len(d.received);d.sockets[3].sendto(b'\0',d.remote_cmd);d.tx_commands+=1;d.record('cached_resume_version_probe');end=time.monotonic()+3
    while time.monotonic()<end:d.poll(min(0.25,end-time.monotonic()))
   matches=sum(p in old_versions for p in d.received[first_version:])
   assert matches>=2 and peer not in d.deleted_peers
   # Retain this modem's existing negotiation. No outbound feature/ID packet.
   d.control_peer=peer;d.feature_mask=feature['selected_mask'];d.sent_features=True;d.diag_ids=ids.copy();d.record('same_boot_cached_negotiation_resumed',seed_sha256=hashlib.sha256(seed).hexdigest(),matching_version_replies=matches,not_fresh_handshake=True)
   d.negotiate(peer,feature['remote_mask'],feature['width'],'same_boot_original_features_reasserted');end=time.monotonic()+4
   while time.monotonic()<end:d.poll(min(0.25,end-time.monotonic()))
   assert d.control_peer==peer and peer not in d.deleted_peers
   d.diagnostic_mode(True);d.gnss_logs(True);run_phase('baseline-off')
   # Keep endpoints open so host can inspect the first RF packets, then request
   # exactly one standard online comparison, or stop. Total lifetime <=15min.
   online_done=False
   while time.monotonic()-began<900:
    if (o/'stop-request').exists():assert (o/'stop-request').read_bytes()==b'stop\n';break
    if (o/'online90-request').exists() and not online_done:
     assert (o/'online90-request').read_bytes()==b'online90\n';online_done=True;modem.SetPowerState(dbus.UInt32(3),timeout=30);assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==3;run_phase('comparison-online')
     modem.SetPowerState(dbus.UInt32(power_before),timeout=30);assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power_before;state['power_restored']=True;save()
    d.poll(0.25)
  finally:
   try:
    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   finally:d.close();closed=d.closed
 if int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))!=power_before:modem.SetPowerState(dbus.UInt32(power_before),timeout=30)
 after_dmesg=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after_dmesg);watch_after=json.loads((r/'gnss-assist/watch-state.json').read_text());loc_after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-after-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 c,bad=counts();report=dict(stage=245,cached_same_boot_resume=True,original_features_reasserted=True,fresh_feature_handshake=False,matching_version_replies=matches,phases=phases,log_counts=c,invalid_log_lengths=bad,diag_decode_errors=d.decode_errors,diag_rx_records=d.records,diag_rx_bytes=d.bytes,mask_zero_reset_request_sent=d.log_mask_reset_sent,realtime_release_request_sent=not d.mode_enabled,closed=closed,original_nv_sources_preserved=True,mm_power_restored=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power_before,location_preserved=all(loc_before[k]==loc_after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),watch_preserved=not watch_after['active'] and all(watch_before[k]==watch_after[k] for k in ['worker_starts','worker_completions']),package_db_preserved=pkg==Path('/lib/apk/db/installed').read_bytes(),fault_delta={k:after_dmesg.count(v)-before_dmesg.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert closed and not bad and not d.decode_errors and all(report[k] for k in ['mm_power_restored','location_preserved','watch_preserved','package_db_preserved']) and report['taint']==0 and not any(report['fault_delta'].values());state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 failure=traceback.format_exc();(o/'failure-private.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
  if d and not d.closed:d.close()
  if props is not None and power_before is not None and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))!=power_before:modem.SetPowerState(dbus.UInt32(power_before),timeout=30)
 except BaseException:(o/'cleanup-failure-private.txt').write_text(traceback.format_exc());failure=failure or 'cleanup failure'
 if bus:bus.close()
 if failure:state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1,diag_closed=bool(d and d.closed));save()
if failure:raise SystemExit(1)
