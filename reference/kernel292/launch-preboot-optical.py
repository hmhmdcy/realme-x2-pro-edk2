"""Use the already verified physical tool after the user's scene adjustment."""
from pathlib import Path
import base64,json
import host
ROOT=Path(__file__).resolve().parent
data=(ROOT.parent/'kernel291/native-physical.py').read_text().replace('k291-physical-r1','k292-preboot-optical-r1').replace('stage=291','stage=292').encode()
code=r'''
from pathlib import Path
import base64,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k290-work/boot-id-private.txt').read_bytes()
directory=r/'k292-tools';directory.mkdir(mode=0o700,exist_ok=True)
script=directory/'native-preboot-optical.py';assert not script.exists();script.write_bytes(base64.b64decode(DATA));compile(script.read_bytes(),str(script),'exec')
assert not (r/'k292-preboot-optical-r1').exists()
with (directory/'preboot-optical-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=292,pid=child.pid,start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''.replace('DATA',repr(base64.b64encode(data).decode()))
q=host.ssh('python3 -',input=code.encode(),timeout=20)
p=host.PRIVATE/'preboot-optical-launch-private.json';assert not p.exists();p.write_bytes(q.stdout);print(q.stdout.decode())
