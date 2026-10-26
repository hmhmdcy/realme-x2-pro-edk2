from pathlib import Path
import json
result=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').is_file():continue
 name=(p/'name').read_text().strip()
 if name not in ['ldo1','smps8']:continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 result.append(dict(sysfs=p.name,name=name,path=str(node.resolve()) if node.exists() else None,values={s:(p/s).read_text().strip() for s in ['state','microvolts','num_users'] if (p/s).is_file()}))
print(json.dumps(result))
