"""Check a bounded complete target TMC10 interpolation call."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('knee411',HERE/'knee-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);machine=k.KneeMachine()
rows=[]
for name in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    root=json.loads((P.parent/'kernel410'/(name+'-tmc10-trees-private.json')).read_text())[0]
    leaf=root['core'][0];t=leaf['trigger'];lux=(t[0]+t[1])/2;gain=(t[2]+t[3])/2
    region,curve=machine.tree(root,lux,gain,2,1.2)
    values=struct.unpack('<11f',region)
    p=struct.pack('<7f',2,1.2,values[0],values[1],values[4],values[5],values[6])
    assert curve==machine.knees(p)
    rows.append(dict(variant=name,whole_function_returns_true=True,region_and_knee_block_consistent=True))
print(json.dumps(dict(rows=rows,instructions=machine.instructions,providers=machine.providers),indent=2))
