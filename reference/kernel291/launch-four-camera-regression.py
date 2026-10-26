"""Start the prepared current-boot physical-camera regression once."""
from pathlib import Path
import base64,json
import host

ROOT=Path(__file__).resolve().parent
data=(ROOT/'native-four-camera-regression.py').read_bytes()
code=r'''
from pathlib import Path
import base64,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k290-work/boot-id-private.txt').read_bytes()
script=r/'k291-tools/native-four-camera-regression.py';assert not script.exists();script.write_bytes(base64.b64decode(DATA));compile(script.read_bytes(),str(script),'exec')
assert not (r/'k291-four-camera-regression-r1').exists()
with (r/'k291-tools/four-camera-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=291,pid=child.pid,start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''.replace('DATA',repr(base64.b64encode(data).decode()))
q=host.ssh('python3 -',input=code.encode(),timeout=20)
p=host.PRIVATE/'four-camera291-launch-private.json';assert not p.exists();p.write_bytes(q.stdout)
print(q.stdout.decode())
