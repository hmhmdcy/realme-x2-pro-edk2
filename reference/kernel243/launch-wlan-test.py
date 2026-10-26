from pathlib import Path
import base64,hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
s=(R/'native-window-session.py').read_text().replace('k243-window-clock','k243-wlan-off-clock').replace('gnss243window','gnss243wlan').replace('indoor window opened; other phones receive GPS per user','same opened window; WLAN softblocked only; USB capture')
s=s.replace(" assert Path('/proc/sys/kernel/tainted')", " assert any((p/'type').read_text().strip()=='wlan' and (p/'soft').read_text().strip()=='1' for p in Path('/sys/class/rfkill').glob('rfkill*'))\n assert Path('/proc/sys/kernel/tainted')")
compile(s,'native-wlan-session.py','exec');(R/'native-wlan-session.py').write_text(s)
payloads={name:base64.b64encode(b).decode() for name,b in [('native-wlan-session.py',s.encode()),('native-wlan-control.py',(R/'native-wlan-control.py').read_bytes())]}
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k243-wlan-control').exists() and not (r/'k243-wlan-off-clock').exists()
o=r/'k243-wlan-tools';assert not o.exists();o.mkdir(mode=0o700);hashes={}
for name,payload in PAYLOADS.items():
 b=base64.b64decode(payload);compile(b,name,'exec');(o/name).write_bytes(b);hashes[name]=hashlib.sha256(b).hexdigest()
with (o/'controller-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(o/'native-wlan-control.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=243,controller_started=True,pid=child.pid,sources=hashes)))
'''.replace('PAYLOADS',repr(payloads))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'wlan-launch-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'wlan-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
