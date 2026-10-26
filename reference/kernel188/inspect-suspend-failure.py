import host

code = '''from pathlib import Path
import json,subprocess,re
root=Path('/var/lib/samurai/k188-ssc-pm')
worker=Path('/var/lib/samurai/k188-tools/pm-worker-private.log').read_text()
print(worker)
print(json.dumps(dict(remoteproc_state=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
 trace_exists=Path('/sys/kernel/tracing/instances/k188-ssc-pm').exists(),
 stats=json.loads((root/'trace-stats-private.json').read_text()) if (root/'trace-stats-private.json').exists() else {})))
'''
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'suspend-failure-inspection-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode())
