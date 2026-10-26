from pathlib import Path
import base64,hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
payload={name:base64.b64encode(path.read_bytes()).decode() for name,path in {
 'native-ordered.py':R/'native-ordered.py','loc_decode.py':R.parent/'kernel226/loc_decode.py'}.items()}
code=r'''
from pathlib import Path
import base64,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k241-loc-differential/state-private.json').read_text())['terminal']
p=r/'k241-oem-tools';assert not (r/'k241-loc-ordered').exists()
for name,data in PAYLOAD.items():
 f=p/name;assert not f.exists();f.write_bytes(base64.b64decode(data))
with (p/'worker-private.log').open('xb') as log:
 process=subprocess.Popen(['nohup','python3',str(p/'native-ordered.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(stage=241,dispatched=True,worker_pid=process.pid,context='k241-loc-ordered',maximum_observation_seconds=90)))
'''.replace('PAYLOAD',repr(payload))
run=host.ssh('python3 -',input=code.encode(),timeout=15)
(P/'ordered-launch-host-private.log').write_bytes(run.stdout+run.stderr)
print(run.stdout.decode())
