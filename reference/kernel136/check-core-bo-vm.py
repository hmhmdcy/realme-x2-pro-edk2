from pathlib import Path
import json
import re

out=Path('/mnt/e/edk2-samurai-out/kernel136')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
p=json.loads((out/'legacy-vm-operations-private.json').read_text())
corr=json.loads((out/'legacy-correlation-private.json').read_text())
t=(out/p['cores'][0]['name']).read_text()
section=re.search(r'^bos:\n(.*?)(?=^[a-z]|\Z)',t,re.S|re.M)[1]
bos=[dict(start=int(m[1],16),size=int(m[2])) for m in re.finditer(r'  - iova: ((?:0x)?[0-9a-fA-F]+)\n    size: ([0-9]+)',section)]
vm_maps=[m for m in corr['same_vm_ops'] if m['op']=='map']
minimum=min(m['start'] for m in vm_maps)
report=dict(stage=136,listed_bos=[dict(size=b['size'],relative_to_fault_vm_min_map=b['start']-minimum,
    exactly_matches_fault_vm_successful_map=any(m['start']==b['start'] and m['size']==b['size'] for m in vm_maps),
    matched_map_vm_count=len(set(m['ttbr'] for m in p['maps'] if m['op']=='map' and m['start']==b['start'] and m['size']==b['size']))) for b in bos],
    fault_relative_to_vm_min_map=p['cores'][0]['fault_iova']-minimum,
    fault_vm_map_sizes=[m['size'] for m in vm_maps],root_cause_proven=False,goal_complete=False)
(ref/'core-bo-vm-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
