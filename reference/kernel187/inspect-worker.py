from pathlib import Path
import json
import host

pid=int((host.PRIVATE/'a11-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k186-reboot-runtime-r2/boot-id-private.txt').read_bytes()
p=Path('/proc/%d/cmdline')
live=p.exists() and b'test-a11-trial.sh' in p.read_bytes()
root=Path('/var/lib/samurai/k187-a11-trial')
report=dict(worker_handle_live=live,worker_proc_exists=p.exists(),
    slpi=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
    power=Path('/sys/devices/platform/sensor-power/state').read_text().strip())
for name in ['start-exit.txt','attributes-exit.txt','light-exit.txt','trial-exit.txt','stop-exit.txt']:
    q=root/name
    if q.exists():report[name]=q.read_text().strip()
attrs=root/'attributes/summary.json'
if attrs.exists():
    d=json.loads(attrs.read_text())
    report['attribute_census_complete']=d['complete']
    report['suid_counts']=d['suid_types']
    report['data_types']=sorted({value for item in d['inventory'] for value in item.get('data_type',[]) if isinstance(value,str)})
print(json.dumps(report))
'''%pid
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'worker-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode().strip())
