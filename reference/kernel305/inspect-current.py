from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,shutil,subprocess
root=Path('/var/lib/samurai/k305-geometry-r2')
pre=json.loads((root/'preflight-private.json').read_text());u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
managers=[]
for name in ['pipewire','wireplumber']:
 item=pre['services'][name]
 assert Path('/proc',str(item['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
 q=subprocess.run(['rc-service','--user',name,'status'],preexec_fn=demote,env=item['env'],capture_output=True,timeout=8)
 (root/(name+'-manager-before-private.log')).write_bytes(q.stdout+q.stderr)
 managers.append(dict(name=name,exit=q.returncode,stopped=q.returncode==3))
q=subprocess.run(['/usr/bin/cam','--help'],capture_output=True,timeout=8);(root/'cam-help-private.txt').write_bytes(q.stdout+q.stderr)
print(json.dumps(dict(stage=305,managers=managers,all_pcm_closed=all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')),
 tools={name:shutil.which(name) for name in ['cam','v4l2-ctl','media-ctl','depmod','modprobe']},cam_help_exit=q.returncode)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
d=json.loads(q.stdout);(HERE/'current-managers-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
