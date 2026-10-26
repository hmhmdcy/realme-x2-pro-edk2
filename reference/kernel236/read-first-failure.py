"""Inspect the terminal first attempt; do not re-probe or power the sensor."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k236-first-failure';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
state=json.loads((root/'k236-runtime/state-private.json').read_text())
assert state['state']=='terminal' and state['exit_code']==1
out.mkdir(mode=0o700)
failure=(root/'k236-runtime/failure-private.txt').read_text()
(out/'observer-failure-private.txt').write_text(failure)
log=subprocess.check_output(['dmesg'],text=True)
(out/'dmesg-private.txt').write_text(log)
filtered=[line for line in log.splitlines() if any(key in line.lower() for key in ['pm8008','imx319','probe with driver'])]
props={}
p=Path('/sys/bus/i2c/devices/1-0008/of_node')
for node in [p,p/'regulators',p/'regulators/ldo1',p/'regulators/ldo4']:
 props[str(node.relative_to(p.parent))]=sorted(child.name for child in node.iterdir() if child.is_file())
(out/'of-properties-private.json').write_text(json.dumps(props,indent=2)+'\n')
report=dict(stage=236,observer_exit=1,failure_tail=failure.splitlines()[-5:],pmic_log=filtered,of_property_names=props,
            no_reprobe_or_power_change=True)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=25)
(host.PRIVATE / 'first-failure-read-host-private.json').write_bytes(result.stdout)
print(result.stdout.decode().strip())
