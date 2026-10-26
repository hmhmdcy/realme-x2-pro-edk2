"""Probe actual TMC11 generation with a decoded region and explicit test statistics."""
from pathlib import Path
import importlib.util,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('generation413',HERE/'generation-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.GenerationMachine()
root=json.loads((P.parent/'kernel412/sunny_s5kgw1-tmc11-trees-private.json').read_text())[0]
node=root['core'][0]
while 'children' in node:node=node['children'][0]
data=node['data'];floats=[]
for v in data.values():floats.extend(v if isinstance(v,list) else [v])
assert len(floats)==44
region=struct.pack('<44f',*floats);gamma=struct.pack('<257f',*[i*1023/256 for i in range(257)])
rows=[]
for kind,hist in [('none',None),('uniform',struct.pack('<1024I',*([64]*1024))),('black',struct.pack('<1024I',65536,*([0]*1023)))]:
    result=target.generate(region,struct.pack('<2f',2,1.2),gamma,hist)
    (P/(kind+'-adrc-private.bin')).write_bytes(result['adrc']);(P/(kind+'-processed-hist-private.bin')).write_bytes(result['processed_hist'])
    values=struct.unpack('<1059f',result['adrc']);rows.append(dict(kind=kind,instructions=result['instructions'],nonfinite_fields=sum(not math.isfinite(v) for v in values[4:]),changed_region_fields=sum(a!=b for a,b in zip(region,result['region']))))
(P/'probe-region-private.bin').write_bytes(region);(P/'probe-gamma-private.bin').write_bytes(gamma)
print(json.dumps(dict(rows=rows,providers=target.providers),indent=2))
