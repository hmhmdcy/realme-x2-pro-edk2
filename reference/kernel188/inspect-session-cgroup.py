import host

code = '''from pathlib import Path
import subprocess,json
sessions=subprocess.check_output(['loginctl','list-sessions','--no-legend'],text=True)
found=[]
for line in sessions.splitlines():
 sid=line.split()[0]
 raw=subprocess.check_output(['loginctl','show-session',sid,'-p','User','-p','Seat','-p','Type','-p','Active','-p','Leader'],text=True)
 d=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
 if d.get('User')=='10000' and d.get('Type')=='wayland' and d.get('Seat')=='seat0' and d.get('Active')=='yes':
  found.append(d)
assert len(found)==1
record=found[0]
record['cgroup']=(Path('/proc')/record['Leader']/'cgroup').read_text()
Path('/var/lib/samurai/k188-desktop-policy/active-session-cgroup-private.json').write_text(json.dumps(record))
print(json.dumps(dict(active_wayland_session_found=True,cgroup_hierarchies=[line.split(':')[1] for line in record['cgroup'].splitlines()])))
'''
p=host.ssh('python3 -',input=code.encode())
print(p.stdout.decode())
