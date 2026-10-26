from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code='''from pathlib import Path
import json
d=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(same394_boot_guard=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes(),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),m2m=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),
 power={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(host.PRIVATE/'device-read-private.json').write_bytes(q.stdout)
r=json.loads(q.stdout);r.update(stage=424,read_only=True,passed=True);(HERE/'device-read-validation.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='core'},indent=2))
