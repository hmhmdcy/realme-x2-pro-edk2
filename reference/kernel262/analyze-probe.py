"""Export only buffer metadata/counts; retain full diagnostics privately."""
from pathlib import Path
import json,sys
import host
delay=int(sys.argv[1]);assert delay in [0,40000,1000000,2000000,2000001,3000000,3000001,3000002,4000000]
code=r'''
from pathlib import Path
import json,re,sys
p=Path('/var/lib/samurai')/('k262-pipewire-'+sys.argv[1]+'-r2')
assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
s=(p/'stderr-private.txt').read_text(errors='replace')
print(json.dumps(dict(stage=262,scenario_code=int(sys.argv[1]),buffer_not_recycled=s.count('was not recycled'),queue_failed=s.count("can't queue recycled"),new_buffers=s.count('got new buffer'),recycle_calls=s.count('recycle buffer'),errors=[l for l in s.splitlines() if 'ERROR' in l][-8:],summary=json.loads((p/'summary.json').read_text()))))
'''
r=host.ssh('python3 - '+str(delay),input=code.encode())
(host.PRIVATE/('analysis-'+str(delay)+'-private.json')).write_bytes(r.stdout)
d=json.loads(r.stdout)
(Path(__file__).parent/('flow-'+str(delay)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k!='summary'},indent=2))
