"""Reuse the validated bounded clock capture with new output and genpd/log reads."""
from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
s=(R.parent/'kernel242/native-clock-session.py').read_text().replace('stage=242','stage=243').replace('k242-clock-session','k243-window-clock').replace('gnss242','gnss243window')
s=s.replace("gpio='/sys/kernel/debug/gpio'","gpio='/sys/kernel/debug/gpio',genpd='/sys/kernel/debug/pm_genpd/pm_genpd_summary'")
s=s.replace(" (out/(label+'-private.json')).write_text", " for name in ['tftp','rmtfs']:\n  p=Path('/run/samurai-wifi')/(name+'.log')\n  if p.is_file():\n   assert p.stat().st_size<32*1024*1024\n   (out/(label+'-'+name+'-private.log')).write_bytes(p.read_bytes())\n (out/(label+'-private.json')).write_text")
s=s.replace('clock_regulator_gpio_reads_only=True','environment="indoor window opened; other phones receive GPS per user",clock_regulator_gpio_reads_only=True')
compile(s,'native-window-session.py','exec');(R/'native-window-session.py').write_text(s)
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k243-window-clock').exists()
o=r/'k243-window-tools';assert not o.exists();o.mkdir(mode=0o700)
p=o/'native-window-session.py';p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec')
with (o/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=243,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(base64.b64encode(s.encode()).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'window-launch-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout)
(R/'window-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
