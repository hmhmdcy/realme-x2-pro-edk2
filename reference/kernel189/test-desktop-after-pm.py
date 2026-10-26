"""Validate the real local desktop user again after all three PM cycles."""
from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent;host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
assert all(json.loads((ref/name).read_text())['suspend_and_sensor_resume_passed'] for name in
 ['persistent-suspend-validation.json','persistent-suspend-r2-validation.json','persistent-suspend-r3-validation.json'])
for name in ['inspect-desktop-policy.py','inspect-session-cgroup.py']:
 text=(ref.parent/'kernel188'/name).read_text().replace('k188','k189')
 scope={'__file__':str(ref/name),'__name__':'__main__'}
 exec(compile(text,str(ref/name),'exec'),scope)
for name in ['test-persistent-client.py','test-active-desktop-client.py','run-client-in-active-session.py']:
 text=(ref.parent/'kernel188'/name).read_text().replace('k188','k189')
 path=ref/name;assert not path.exists();path.write_text(text)
 dest='/var/lib/samurai/k189-tools/'+name if name.startswith('run-') else '/usr/share/samurai/ssc/'+name
 host.upload(path,dest);host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
 if name.startswith('test-'):host.ssh('chmod 644 '+dest)
text=(ref.parent/'kernel188/verify-persistent-runtime.py').read_text().replace('k188','k189')
text=text.replace('k189-reboot-runtime','k189r2-reboot-runtime')
text=text.replace("['su', '-s', '/bin/sh', 'cy122', '-c', 'python3 /var/lib/samurai/k189-tools/test-persistent-client.py']",
 "['python3', '/var/lib/samurai/k189-tools/run-client-in-active-session.py']")
try:p=host.ssh('python3 -',input=text.encode(),timeout=100)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'desktop-after-pm-failure-private.log').write_bytes(error.stdout+error.stderr);raise
(host.PRIVATE/'desktop-after-pm-host-private.log').write_bytes(p.stdout+p.stderr)
record=json.loads(p.stdout);record.update(stage=189,after_three_sensor_suspend_cycles=True)
(ref/'desktop-after-pm-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
