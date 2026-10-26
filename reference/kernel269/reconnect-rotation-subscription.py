"""Refresh the desktop's standard rotation lock setting after sensor restart."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,os,pwd,subprocess,time
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
env={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
u=pwd.getpwuid(10000);os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid);os.environ.update(env)
args=['gsettings'];schema='org.gnome.settings-daemon.peripherals.touchscreen';key='orientation-lock'
before=subprocess.check_output(args+['get',schema,key],text=True).strip();assert before=='false'
try:
 subprocess.run(args+['set',schema,key,'true'],check=True);time.sleep(1)
finally:subprocess.run(args+['set',schema,key,before],check=True)
time.sleep(2)
print(json.dumps(dict(before=before,after=subprocess.check_output(args+['get',schema,key],text=True).strip(),
 app_source_changed=False,manual_display_transform_applied=False)))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=15);(P/'rotation-subscription-private.json').write_bytes(q.stdout);print(q.stdout.decode())
