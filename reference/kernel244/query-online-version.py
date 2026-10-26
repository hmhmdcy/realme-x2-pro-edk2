"""Read-only VERSION on an observed command endpoint, without control fallback."""
from pathlib import Path
import dbus,json,os,struct,sys,time
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k244-online-version';assert not o.exists();o.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);assert int(v['org.freedesktop.ModemManager1.Modem']['PowerState'])==3 and int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled'])==0;bus.close()
sys.path.insert(0,str(r/'k244-diag-python-r1'));from diag_transport import Diag
d=None;replies=[]
with (o/'events-private.jsonl').open('x') as output:
 try:
  d=Diag(output);end=time.monotonic()+3
  while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
  assert d.remote_cmd
  d.sockets[3].sendto(b'\0',d.remote_cmd);d.tx_commands+=1;d.record('version_only_without_control_message')
  end=time.monotonic()+5
  while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
  replies=[dict(code=x[0],bytes=len(x)) for x in d.received if x]
 finally:
  if d:d.close()
report=dict(stage=244,mm_power_online=True,replies=replies,control_messages_sent=d.tx_control,version_only=True,transport_closed=d.closed)
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'events':[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()]}}))
