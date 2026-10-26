"""Enumerate only advertised sensor modes and current connection state."""
from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import json,subprocess
codes={'s5kgw1':'0x300e','imx471':'0x300f','imx319':'0x300f','s5k3m5':'0x300a'}
result={'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),'sensors':{}}
for p in Path('/sys/class/video4linux').glob('v4l-subdev*'):
    model=(p/'name').read_text().split()[0]
    if model not in codes:continue
    q=subprocess.run(['v4l2-ctl','-d','/dev/'+p.name,'--list-subdev-framesizes','pad=0,code='+codes[model]],capture_output=True,text=True)
    result['sensors'][model]={'exit':q.returncode,'formats':q.stdout,'error':q.stderr}
print(json.dumps(result,indent=2))
'''
data=host.raw_ssh('python3 -c '+shlex.quote(code)).stdout
(Path(__file__).resolve().parent/'mode-enumeration.json').write_bytes(data)
print(data.decode())
