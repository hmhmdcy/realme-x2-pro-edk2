from pathlib import Path
import json,sys
import host
which,kind=sys.argv[1:];assert (which,kind) in [('rear','raw'),('front','raw'),('front','rgb')]
code=r'''
from pathlib import Path
import json,sys
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
which,kind=sys.argv[1:];p=r/f'k237-capture-{which}-{kind}-r2';s=json.loads((p/'state-private.json').read_text());assert s['state']=='terminal'
files={n:(p/n).read_text(errors='replace') for n in ['failure-private.txt','stderr-private.txt','stdout-private.json'] if (p/n).exists()}
print(json.dumps(files))
'''
r=host.ssh('python3 - '+which+' '+kind,input=code.encode(),timeout=12);(host.PRIVATE/f'{which}-{kind}-r2-failure-details-private.json').write_bytes(r.stdout)
data=json.loads(r.stdout);print(json.dumps(dict(failure_tail=data.get('failure-private.txt','').splitlines()[-4:],stderr_tail=data.get('stderr-private.txt','').splitlines()[-14:],stdout_present=bool(data.get('stdout-private.json')))))
