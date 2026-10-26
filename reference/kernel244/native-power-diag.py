"""Observe DIAG across a normal MM power-on; GNSS only if fresh transport works."""
from pathlib import Path
import dbus,hashlib,json,os,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k244-power-diag';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=244,state='preflight',terminal=False,pid=os.getpid());bus=None;diag=None;child=None;error=None;power_changed=False;responses=[];session=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def mode(label):
 x=subprocess.run(['qmicli','-p','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=20);(o/(label+'-mode-private.txt')).write_bytes(x.stdout+x.stderr);assert x.returncode==0
 return next((n for n in ['shutting-down','online','low-power','offline'] if "'"+n+"'" in x.stdout.decode()),None)
save();before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
 bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path=next(str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v)
 obj=bus.get_object(owner,path);props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem');loc_before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 assert int(loc_before['Enabled'])==0 and not loc_before['SignalsLocation'] and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1
 watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert not watch['active'] and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert mode('before')=='shutting-down';db=Path('/lib/apk/db/installed').read_bytes()
 sys.path.insert(0,str(r/'k244-diag-python-r1'));from diag_transport import Diag,regression
 regression()
 with (o/'diag-events-private.jsonl').open('x') as output:
  diag=Diag(output)
  try:
   end=time.monotonic()+3
   while time.monotonic()<end:diag.poll(min(0.5,end-time.monotonic()))
   state.update(state='power_on_requested');save();api.SetPowerState(dbus.UInt32(3),timeout=50);power_changed=True
   state.update(state='power_on_ack',dms_mode=mode('online'));save();assert state['dms_mode']=='online'
   end=time.monotonic()+10
   while time.monotonic()<end:diag.poll(min(0.5,end-time.monotonic()))
   if diag.sent_features and diag.remote_cmd:
    for i in range(2):
     reply=diag.query(b'\x00');responses.append(dict(present=reply is not None,code=reply[0] if reply else None,bytes=len(reply) if reply else 0))
    if all(v['present'] and v['code']==0 for v in responses):
     tool=r/'k226-loc-tools-r3';build=json.loads((tool/'build-summary.json').read_text());assert hashlib.sha256((tool/'loc-session').read_bytes()).hexdigest()==build['binary_sha256'] and build['fixed_observation_seconds']==90 and build['message_allowlist']==[33,34,35,50,51,63,75]
     diag.gnss_logs(True)
     with (o/'loc-events-private.jsonl').open('xb') as out,(o/'loc-stderr-private.txt').open('xb') as err:
      env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None);child=subprocess.Popen([str(tool/'loc-session'),'high'],stdout=out,stderr=err,env=env);state.update(state='gnss_running',child_pid=child.pid);save();deadline=time.monotonic()+170
      while child.poll() is None:
       if time.monotonic()>deadline:raise RuntimeError('GNSS deadline')
       diag.poll(0.5)
     assert child.returncode==0;session=json.loads((o/'loc-events-private.jsonl').read_text().splitlines()[-1]);assert all(session[k] for k in ['stop_ack','client_released','device_closed'])
  finally:
   try:
    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   finally:diag.close()
 (o/'qrtr-after-private.txt').write_bytes(subprocess.check_output(['qrtr-lookup']))
 loc_after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');watch_after=json.loads((r/'gnss-assist/watch-state.json').read_text());after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after)
 report=dict(stage=244,power_on_ack=power_changed,dms_after=mode('final'),mm_power_after=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState')),power_on_retained_for_diagnostic_followup=True,
  fresh_control_feature_received=bool(diag.feature_mask),version_responses=responses,diag_rx_packets=diag.records,diag_decode_errors=diag.decode_errors,diag_closed=diag.closed,gnss_started=child is not None,gnss_cleanup=session,
  location_preserved=all(loc_before[k]==loc_after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),watch_preserved=not watch_after['active'] and all(watch[k]==watch_after[k] for k in ['worker_starts','worker_completions']),package_db_preserved=db==Path('/lib/apk/db/installed').read_bytes(),
  no_modem_reset_or_nv_commands=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()})
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert report['location_preserved'] and report['watch_preserved'] and report['package_db_preserved'] and not any(report['fault_delta'].values()) and report['taint']==0
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(o/'failure-private.txt').write_text(error);state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1,power_on_ack=power_changed);save()
finally:
 if bus:bus.close()
if error:raise SystemExit(1)
