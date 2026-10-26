"""Unblank the configured desktop through its standard ScreenSaver interface."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,os,pwd,subprocess,time
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
env={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.SetActive','false'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
time.sleep(1)
report=dict(exit=q.returncode,response=q.stdout,stderr=q.stderr,
 connectors={str(p):{n:(p/n).read_text().strip() for n in ['status','enabled','dpms'] if (p/n).is_file()} for p in Path('/sys/class/drm').glob('card*-DSI-*')},
 taint=Path('/proc/sys/kernel/tainted').read_text().strip())
print(json.dumps(report))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=15);(P/'unblank-private.json').write_bytes(q.stdout);print(q.stdout.decode())
