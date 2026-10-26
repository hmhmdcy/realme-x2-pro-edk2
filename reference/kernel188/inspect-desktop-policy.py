from pathlib import Path
import json
import host

code = '''from pathlib import Path
import json,subprocess,os
root=Path('/var/lib/samurai/k188-desktop-policy')
root.mkdir(mode=0o700,exist_ok=True)
sessions=subprocess.check_output(['loginctl','list-sessions','--no-legend'],text=True)
(root/'sessions-private.txt').write_text(sessions)
parsed=[]
for line in sessions.splitlines():
 sid=line.split()[0]
 props=subprocess.check_output(['loginctl','show-session',sid,'-p','User','-p','Active','-p','State','-p','Class','-p','Seat','-p','Type'],text=True)
 d=dict(x.split('=',1) for x in props.splitlines() if '=' in x)
 if d.get('User')=='10000':parsed.append(d)
pids=subprocess.check_output(['pidof','phosh'],text=True).split()
assert len(pids)==1
env=dict(item.split(b'=',1) for item in (Path('/proc')/pids[0]/'environ').read_bytes().split(b'\\0') if b'=' in item)
address=env[b'DBUS_SESSION_BUS_ADDRESS'].decode()
(root/'session-address-private.txt').write_text(address)
policies=[]
for p in Path('/usr/share/polkit-1/actions').glob('*Sensor*'):
 policies.append(str(p))
 (root/p.name).write_bytes(p.read_bytes())
 print(p.read_text())
print(json.dumps(dict(desktop_sessions=parsed,session_bus_present=bool(address),policy_files=len(policies))))
'''
p = host.ssh('python3 -', input=code.encode())
(host.PRIVATE / 'desktop-policy-inspection-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode())
