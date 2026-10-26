import json
import host

code='''from pathlib import Path
import json,re
lines=Path('/var/lib/samurai/k190-mm-reinit-r2/daemon-debug-private.log').read_text().splitlines()
packets=[]
for i,line in enumerate(lines):
 if 'message     = "Get Predicted Orbits Data Source"' not in line:continue
 fields=[v.strip() for v in lines[max(0,i-18):i+2] if any(k in v.lower() for k in ['flags','type','service','transaction','message','client'])]
 packets.append(fields)
print(json.dumps(dict(packets=packets)))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'orbit-wire-order-private.json').write_bytes(p.stdout);print(p.stdout.decode())
