"""Read current launchers and crash monitor settings; do not start a camera."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
u=pwd.getpwuid(10000);home=Path(u.pw_dir)
files={}
for root in [home/'.local/share/applications',home/'.local/share/dbus-1/services',Path('/usr/share/samurai/user-config/applications'),Path('/usr/share/samurai/user-config/dbus-1/services')]:
 for p in root.glob('*Snapshot*'):
  if p.is_file():files[str(p)]=[l for l in p.read_text().splitlines() if l.startswith(('Exec=','DBusActivatable=','Name='))]
report=dict(launchers=files,
 remoteprocs={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip(),
 recovery=(p/'recovery').read_text().strip() if (p/'recovery').is_file() else None) for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
 core_pattern=Path('/proc/sys/kernel/core_pattern').read_text().strip(),
 taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
 fault_counts={k:subprocess.check_output(['dmesg']).count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',modem=b'crash detected in modem',fatal=b'fatal error received',gpu=b'gpu fault:').items()})
print(json.dumps(report))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=20);(P/'camera-launchers-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps(d,indent=2))
