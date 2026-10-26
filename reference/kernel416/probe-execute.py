"""Bounded complete-function probe with existing native ADRC storage."""
from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('execute416',HERE/'execute-model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);target=m.ExecuteMachine();target.reset()
root=json.loads((P.parent/'kernel412/sunny_s5kgw1-tmc11-trees-private.json').read_text())[0]
result=target.request(root,[2,1.2,2,140,3,4],0,[0,0],1)
(P/'whole-execute-probe-adrc-private.bin').write_bytes(result['adrc'])
print(json.dumps(dict(returned_complete=True,output_bytes=len(result['adrc']),instructions=result['instructions'],providers=target.providers)))
