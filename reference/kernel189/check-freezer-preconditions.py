import json
import subprocess
import host

code='''from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189-reboot-runtime/boot-id-private.txt').read_bytes()
control=Path('/sys/kernel/debug/dynamic_debug/control')
rows=[line for line in control.read_text().splitlines() if 'fastrpc_internal_invoke ' in line]
report=dict(pm_test=Path('/sys/power/pm_test').read_text().strip(),
 dynamic_debug_function_sites=len(rows),slpi=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip())
print(json.dumps(report))
assert '[none]' in report['pm_test'] and 'freezer' in report['pm_test'] and rows
'''
try:p=host.ssh('python3 -',input=code.encode())
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'freezer-precondition-failure-private.log').write_bytes(error.stdout+error.stderr)
 print(error.stdout.decode()+error.stderr.decode());raise
print(p.stdout.decode())
