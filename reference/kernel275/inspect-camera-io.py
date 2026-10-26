from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
node=Path('/sys/bus/i2c/devices/6-0010/of_node');handle=(node/'vddio-supply').read_bytes()
base=Path('/sys/firmware/devicetree/base');matches=[]
for p in base.rglob('phandle'):
 if p.read_bytes()==handle:matches.append(p.parent)
assert len(matches)==1;target=matches[0];rows=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 row=dict(name=(p/'name').read_text().strip(),path=str(p),of_nodes=[])
 for rel in ['of_node','device/of_node']:
  if (p/rel).exists():row['of_nodes'].append(str((p/rel).resolve()))
 for key in ['state','num_users','microvolts']:
  try:row[key]=(p/key).read_text().strip()
  except OSError:pass
 rows.append(row)
print(json.dumps(dict(vio_node=str(target),vio_name=(target/'regulator-name').read_bytes().split(b'\0')[0].decode() if (target/'regulator-name').exists() else None,regulators=rows)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);d=json.loads(q.stdout);(host.PRIVATE/'camera-io-supply-private.json').write_text(json.dumps(d,indent=2)+'\n')
matches=[r for r in d['regulators'] if d['vio_node'] in r['of_nodes'] or r['name']==d['vio_name']]
print(json.dumps(dict(vio_node=d['vio_node'],vio_name=d['vio_name'],matches=matches),indent=2))
