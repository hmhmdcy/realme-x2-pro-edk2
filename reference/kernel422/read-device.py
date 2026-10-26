"""Check whether the current device can support the next physical experiment."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code='''from pathlib import Path
import json
dev=Path('/sys/bus/platform/devices/ac10000.icp')
guard=Path('/var/lib/samurai/k394-recovered/boot-id-private.txt')
print(json.dumps(dict(same394_boot_guard=guard.read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),m2m=json.loads((dev/'m2m_status').read_text()),
 core=json.loads((dev/'state').read_text()),power={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
try:
    q=host.ssh('python3 -c '+shlex.quote(code),timeout=25)
    (host.PRIVATE/'device-read-private.json').write_bytes(q.stdout)
    data=json.loads(q.stdout);data.update(stage=422,read_only=True,new_hardware_frames=0,passed=True)
    (HERE/'device-read-validation.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:data[k] for k in ['stage','same394_boot_guard','taint','m2m','power','read_only','passed']},indent=2))
except Exception as e:
    data=dict(stage=422,read_only=True,passed=False,error=str(e),new_hardware_frames=0)
    (HERE/'device-read-validation.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));raise
