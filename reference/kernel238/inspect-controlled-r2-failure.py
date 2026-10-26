from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k238-controlled-rear-r14-r2';assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
print(json.dumps({n:(p/n).read_text(errors='replace') for n in ['failure-private.txt','stderr-private.txt','stdout-private.json','i2c-control-trace-private.txt'] if (p/n).exists()}))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'controlled-r2-failure-details-private.json').write_bytes(r.stdout);data=json.loads(r.stdout)
print(json.dumps(dict(failure=data.get('failure-private.txt','').splitlines()[-4:],stderr_tail=data.get('stderr-private.txt','').splitlines()[-26:],stdout=data.get('stdout-private.json','')[:300],trace_lines=len(data.get('i2c-control-trace-private.txt','').splitlines()))))
