from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
p=Path('/proc/2261');assert (p/'comm').read_text().strip()=='phosh' and (p/'stat').read_text().rsplit(')',1)[1].split()[19]=='1967'
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]};env={k:v for k,v in raw.items() if k in ['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS']};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
results=[]
for args in [['/var/lib/samurai/k265-tools/pw-metadata','--help'],['/var/lib/samurai/k265-tools/pw-metadata','-n','settings'],['wpctl','inspect','0']]:
 q=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,timeout=8);results.append(dict(args=args,exit_code=q.returncode,output=(q.stdout+q.stderr).decode()))
print(json.dumps(results,indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'metadata-before-private.json').write_bytes(q.stdout);print(q.stdout.decode())
