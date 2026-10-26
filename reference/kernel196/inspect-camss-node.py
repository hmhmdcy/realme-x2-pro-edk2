from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k196-baseline/boot-id-private.txt').read_bytes()
dt=Path('/sys/firmware/devicetree/base');nodes=[]
for p in (dt/'soc@0').iterdir():
 if p.name.startswith('camss@'):nodes.append(dict(path=str(p).split('/base')[-1],status=(p/'status').read_bytes().decode().strip('\0'),ports_exist=(p/'ports').exists(),ports_children=[v.name for v in (p/'ports').iterdir()] if (p/'ports').exists() else []))
assert len(nodes)==1;Path('/var/lib/samurai/k196-baseline/camss-node.json').write_text(json.dumps(nodes[0],indent=2)+'\n');print(json.dumps(nodes[0]))
