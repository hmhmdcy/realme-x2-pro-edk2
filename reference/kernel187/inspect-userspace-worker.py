from pathlib import Path
import host

pid=int((host.PRIVATE/'userspace-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k187-reboot-runtime/boot-id-private.txt').read_bytes()
p=Path('/proc/%d/cmdline')
live=p.exists() and b'test-a11-userspace-trial.sh' in p.read_bytes()
root=Path('/var/lib/samurai/k187-a11-userspace')
result=dict(worker_handle_live=live,worker_proc_present=p.exists(),
    slpi=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
    sensor_power=Path('/sys/devices/platform/sensor-power/state').read_text().strip())
for name in ['start-exit.txt','userspace-exit.txt','trial-exit.txt','stop-exit.txt']:
    path=root/name
    if path.exists():result[name]=path.read_text().strip()
for name in ['accel','gyro','mag']:
    path=root/'userspace'/name/'summary.json'
    if path.exists():result[name]=json.loads(path.read_text())
path=root/'userspace/summary.json'
if path.exists():result['userspace']=json.loads(path.read_text())
print(json.dumps(result))
'''%pid
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'userspace-worker-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode().strip())
