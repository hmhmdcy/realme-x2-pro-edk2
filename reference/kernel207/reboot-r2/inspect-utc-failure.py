import host

native = r'''
from pathlib import Path
import json, shutil, subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k207r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k207r2-utc-inspection';out.mkdir(mode=0o700)
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
for name in ['watch-state.json','prepare-time-stdout-private.json','prepare-time-stderr-private.txt']:
    source=root/'gnss-assist'/name
    if source.is_file():shutil.copyfile(source,out/name)
chrony=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10)
(out/'chrony-private.txt').write_text(chrony.stdout+chrony.stderr)
print(json.dumps(dict(uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),time_prepared=watch.get('time_prepared'),time_preparation_last_result=watch.get('time_preparation_last_result'),chrony_normal=chrony.returncode==0 and 'Normal' in chrony.stdout)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=25)
(host.PRIVATE/'utc-inspection-host-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
