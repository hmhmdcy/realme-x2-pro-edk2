"""Read current sensor geometry and control ranges without starting capture."""
from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import json,os,subprocess
models=['s5kgw1','imx471','imx319','s5k3m5']
result={'kernel':os.uname().release,'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
        'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'sensors':{}}
for model in models:
    nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip().startswith(model+' ')]
    if len(nodes)!=1:raise RuntimeError('Expected one '+model)
    node='/dev/'+nodes[0].name
    q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls','--get-subdev-fmt','pad=0'],capture_output=True,text=True,timeout=10)
    if q.returncode:raise RuntimeError(q.stderr)
    result['sensors'][model]={'node':node,'controls_and_format':q.stdout}
print(json.dumps(result,indent=2))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30)
data=json.loads(q.stdout)
(host.PRIVATE/'sensor-state.json').write_bytes(q.stdout)
print(json.dumps(data,indent=2))
