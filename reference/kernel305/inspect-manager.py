from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
root=Path('/var/lib/samurai/k305-sensor-candidate')
pre=json.loads((root/'preflight-private.json').read_text())
user=pwd.getpwuid(10000)
def demote():
 os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
results=[]
for name in ['pipewire','wireplumber']:
 item=pre['services'][name]
 assert Path('/proc',str(item['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
 q=subprocess.run(['rc-service','--user',name,'status'],preexec_fn=demote,env=item['env'],capture_output=True,timeout=8)
 (root/(name+'-manager-before-private.log')).write_bytes(q.stdout+q.stderr)
 results.append(dict(name=name,exit=q.returncode,manager_started=q.returncode==0,manager_stopped=q.returncode==3))
assert all(r['exit'] in [0,3] for r in results)
pcm=[p.read_text().strip() for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')]
print(json.dumps(dict(stage=305,managers=results,all_pcm_closed=all(v=='closed' for v in pcm))))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
report=json.loads(q.stdout)
(HERE/'manager-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
