from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import json
base=Path('/sys/firmware/devicetree/base')
names=['/reserved-memory/memory@9ab00000','/soc@0','/soc@0/camss@acb3000','/soc@0/clock-controller@ad00000']
out={}
for name in names:
 p=base/name.lstrip('/');out[name]={k:(p/k).read_bytes().hex() for k in ['phandle','reg','status','no-map','#address-cells','#size-cells'] if (p/k).exists()}
print(json.dumps(out))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(host.PRIVATE/'region-baseline-private.json').write_bytes(q.stdout);print(json.dumps(json.loads(q.stdout),indent=2))
