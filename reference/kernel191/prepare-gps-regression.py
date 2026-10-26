from pathlib import Path
import hashlib,json
ref=Path(__file__).resolve().parent;prior=ref.parent/'kernel190'
utc=(prior/'probe-utc-injection.py').read_text().replace('k190-utc-injection','k191-utc-injection').replace('stage=190','stage=191')
assert 'source.close_async' in utc and 'source.close(' not in utc
(ref/'probe-utc-injection.py').write_text(utc)
stream=(prior/'test-mm-location-stream.py').read_text().replace('k190-mm-stream','k191-mm-stream').replace('stage=190','stage=191').replace('time.monotonic()+125','time.monotonic()+300')
stream=stream.replace("assert not before['SignalsLocation']", """assert not before['SignalsLocation']
validity=json.loads(Path('/var/lib/samurai/k191-validity-after/summary.json').read_text());assert validity['duration_hours']>0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
manager=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.ModemManager1')""")
stream=stream.replace("try:\n api.SetGpsRefreshRate", "try:\n manager.SetLogging('DEBUG')\n api.SetGpsRefreshRate")
stream=stream.replace(" final=props.GetAll", " manager.SetLogging('INFO');summary['logging_restored_to_info']=True\n final=props.GetAll")
(ref/'test-mm-location-stream.py').write_text(stream)
compile(stream,'test-mm-location-stream.py','exec');print('UTC probe and 300-second standard MM GPS regression prepared')
