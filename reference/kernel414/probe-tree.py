"""Bounded ABI probe before generating the full interpolation corpus."""
from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('tree414',HERE/'tree-model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);target=m.TreeMachine()
roots=json.loads((P.parent/'kernel412/sunny_s5kgw1-tmc11-trees-private.json').read_text())
rows=[]
for root in roots:
    raw,nodes,instructions=target.tree(root,root['control_method'],[2,2,50,2,2])
    rows.append(dict(uid=root['uid'],nodes=nodes,instructions=instructions,bytes=len(raw)))
    (P/('probe-root'+str(root['uid'])+'-private.bin')).write_bytes(raw)
(P/'probe-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(dict(roots=len(rows),bytes_per_region=176,instructions=target.instructions,providers=target.providers)))
