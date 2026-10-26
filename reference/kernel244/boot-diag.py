"""One boot only, expires after 12 minutes; all diagnostic data stays private."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time,traceback
os.umask(0o077);base=Path('/var/lib/samurai/k244-nextboot');cfg=json.loads((base/'config-private.json').read_text());o=base/'capture';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=244,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);diag=None;child=None;failure=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def stop(signum,frame):raise KeyboardInterrupt('Diagnostic capture stopped')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);save()
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot!=cfg['previous_boot']
 assert Path('/proc/device-tree/model').read_bytes().hex()==cfg['model_hex'] and os.uname().release==cfg['kernel_release']
 runtime=Path('/var/lib/samurai/k244-runtime');assert not runtime.exists();runtime.mkdir(mode=0o700);(runtime/'boot-id-private.txt').write_text(boot+'\n')
 (o/'boot-id-private.txt').write_text(boot+'\n');(o/'dmesg-before-private.txt').write_bytes(subprocess.check_output(['dmesg']))
 sys.path.insert(0,str(base));from diag_transport_boot import Diag,regression
 regression();began=time.monotonic();started=False;armed=False;queries_done=False;versions=[]
 with (o/'diag-events-private.jsonl').open('x') as log:
  diag=Diag(log)
  try:
   Path('/run/samurai-diag244-ready').write_text('published\n');state.update(state='published_before_modem');save();last=0
   while time.monotonic()-began<720 and not (base/'stop-request').exists():
    diag.poll(0.25)
    if diag.sent_features and diag.remote_cmd and not queries_done:
     queries_done=True;state.update(state='fresh_feature_received');save()
     # VERSION queries are read-only; logging does not depend on a version reply.
     for i in range(2):
      reply=diag.query(b'\0',seconds=3);versions.append(dict(present=reply is not None,code=reply[0] if reply else None,bytes=len(reply) if reply else 0))
     state.update(state='ready',versions=versions,diag_ids=len(diag.diag_ids));save()
    if (base/'capture90-request').exists() and not started:
     assert (base/'capture90-request').read_bytes()==b'capture90\n' and diag.sent_features and diag.control_peer
     tools=Path('/var/lib/samurai/k226-loc-tools-r3');assert hashlib.sha256((tools/'loc-session').read_bytes()).hexdigest()==cfg['loc_binary_sha256']
     import dbus
     bus=dbus.SystemBus(private=True)
     try:
      objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x)
      assert int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled'])==0 and not json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_text())['active']
     finally:bus.close()
     diag.diagnostic_mode(True);diag.gnss_logs(True);armed=True
     env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None)
     locout=(o/'loc-events-private.jsonl').open('xb');locerr=(o/'loc-stderr-private.txt').open('xb')
     child=subprocess.Popen([str(tools/'loc-session'),'high'],stdout=locout,stderr=locerr,env=env);started=True;deadline=time.monotonic()+170;state.update(state='gnss_running',child_pid=child.pid);save()
    if child is not None:
     if child.poll() is not None:
      locout.close();locerr.close();assert child.returncode==0
      cleanup=json.loads((o/'loc-events-private.jsonl').read_text().splitlines()[-1]);assert all(cleanup[k] for k in ['stop_ack','client_released','device_closed'])
      state.update(state='gnss_finished',gnss_cleanup=cleanup);save();break
     if time.monotonic()>deadline:raise RuntimeError('GNSS deadline')
    if time.monotonic()-last>3:
     state.update(diag_rx_packets=diag.records,diag_received_payloads=len(diag.received),decode_errors=diag.decode_errors,elapsed_seconds=round(time.monotonic()-began));save();last=time.monotonic()
  finally:
   try:
    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   finally:diag.close()
 report=dict(stage=244,versions=versions,gnss_started=started,logging_armed=armed,diag_packets=diag.records,diag_bytes=diag.bytes,decode_errors=diag.decode_errors,diag_ids=len(diag.diag_ids),mask_zero_reset_sent=diag.log_mask_reset_sent,diagnostic_mode_released=not diag.mode_enabled,closed=diag.closed,control_payloads_sent=diag.tx_control,no_nv_or_rf_configuration_commands=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 failure=traceback.format_exc();(o/'failure-private.txt').write_text(failure);state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1);save()
finally:
 (o/'dmesg-after-private.txt').write_bytes(subprocess.check_output(['dmesg']))
if failure:raise SystemExit(1)
