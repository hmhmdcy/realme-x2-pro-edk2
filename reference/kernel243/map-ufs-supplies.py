"""Resolve live FDT UFS supply phandles; read-only, no assumed PMIC naming."""
from pathlib import Path
import json,struct
tree=Path('/sys/firmware/devicetree/base');nodes={}
for p in tree.rglob('phandle'):
 b=p.read_bytes()
 if len(b)==4:nodes[struct.unpack('>I',b)[0]]=p.parent
rows=[]
for node in tree.rglob('*'):
 if not node.is_dir() or not node.name.startswith(('ufshc@','ufs@')):continue
 for p in node.glob('*-supply'):
  b=p.read_bytes();assert len(b)==4;target=nodes.get(struct.unpack('>I',b)[0]);assert target is not None
  row=dict(controller=node.name,supply=p.name,regulator_node=target.name,regulator_name=(target/'regulator-name').read_bytes().rstrip(b'\0').decode() if (target/'regulator-name').exists() else None)
  for n in ['regulator-min-microvolt','regulator-max-microvolt']:
   if (target/n).exists():row[n]=struct.unpack('>I',(target/n).read_bytes())[0]
  rows.append(row)
report=dict(stage=243,live_device_tree_readonly=True,ufs_supplies=rows,ldo10_references=sum(x['regulator_node']=='ldo10' for x in rows))
assert rows
print(json.dumps(report))
