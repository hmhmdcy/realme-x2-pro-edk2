"""Reannounce configured-size queries without restarting modem or loaning RAM."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k247-configured-query';assert not o.exists();o.mkdir(mode=0o700)
s=dict(stage=247,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);m=None;child=None;failure=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(s,indent=2)+'\n');p.replace(o/'state-private.json')
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes()
 old=json.loads((r/'k247-nextboot/capture/state-private.json').read_text());assert old['terminal'] and old['exit_code']==0 and not Path('/proc',str(old['pid'])).exists()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 from memshare_configured import Memshare
 with (o/'memshare-events-private.jsonl').open('x') as output:
  m=Memshare(output)
  try:
   m.prepare();s.update(state='observing_reannouncement',memshare=m.snapshot());save();began=time.monotonic()
   while time.monotonic()-began<30:
    m.check();time.sleep(0.25)
   # Without a real re-query, a further zero-CNR trial would add no new factor.
   repeat=any(x.get('configured_initial_bytes')==5242880 for x in m.requests)
   if repeat:
    import dbus
    bus=dbus.SystemBus(private=True)
    try:
     objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];w=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(v['org.freedesktop.ModemManager1.Modem']['PowerState'])==1 and int(loc['Enabled'])==0 and not loc['SignalsLocation'] and w['running'] and w['time_prepared'] and not w['active']
    finally:bus.close()
    binary=r/'k226-loc-tools-r3/loc-session';cfg=json.loads((r/'k247-nextboot/config-private.json').read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==cfg['loc_binary_sha256'];env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
    with (o/'loc-events-private.jsonl').open('xb') as out,(o/'loc-stderr-private.txt').open('xb') as err:
     child=subprocess.Popen([str(binary),'high'],stdout=out,stderr=err,env=env);s.update(state='gnss_running',child_pid=child.pid);save();started=time.monotonic()
     while child.poll() is None:
      assert time.monotonic()-started<170;m.check();time.sleep(0.25)
    rows=[json.loads(x) for x in (o/'loc-events-private.jsonl').read_text().splitlines()];assert child.returncode==0 and all(rows[-1][k] for k in ['stop_ack','client_released','device_closed'])
    from loc_decode import summarize
    s['receiver']=summarize(rows);assert not s['receiver']['decode_errors'];s['loc_cleanup']=rows[-1]
   s.update(requery_observed=repeat,gnss_trial_performed=repeat,observation_seconds=round(time.monotonic()-began,2))
  finally:
   if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
   m.close()
 s.update(memshare=m.snapshot(),state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 failure=traceback.format_exc();(o/'failure-private.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
  if m and not m.closed:m.close()
 except BaseException:
  (o/'cleanup-failure-private.txt').write_text(traceback.format_exc());failure=failure or 'cleanup failure'
 if failure:s.update(state='failed',terminal=True,exit_code=1,memshare=m.snapshot() if m else None);save()
if failure:raise SystemExit(1)
