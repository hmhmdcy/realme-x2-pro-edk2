from pathlib import Path
import host,json

code=r'''
from pathlib import Path
import json,os,pwd,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
policies=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()!='wireplumber':continue
        fields=(p/'status').read_text();uid=int(fields.split('Uid:',1)[1].split()[0]);parent=int(fields.split('PPid:',1)[1].split()[0])
        env={k.decode():v.decode() for e in (p/'environ').read_bytes().split(b'\0') if b'=' in e for k,v in [e.split(b'=',1)]}
        def demote():
            u=pwd.getpwuid(uid);os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(uid)
        status=subprocess.run(['rc-service','--user','wireplumber','status'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
        policies.append(dict(pid=int(p.name),uid=uid,parent_comm=Path('/proc',str(parent),'comm').read_text().strip(),status_exit=status.returncode,status=status.stdout+status.stderr))
    except FileNotFoundError:pass
text=Path('/etc/user/init.d/wireplumber').read_text()
(root/'k219-runtime/policy-init-private.txt').write_text(text)
print(json.dumps(dict(policies=policies,init_lines=[l for l in text.splitlines() if any(x in l for x in ['command','supervisor','pidfile'])])))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'policy-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode().strip())
