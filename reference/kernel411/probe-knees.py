"""Compare the actual target knees with the prior source-only reference."""
from pathlib import Path
import importlib.util,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('knee411',HERE/'knee-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);machine=k.KneeMachine()
inputs=(P.parent/'kernel410/tmc-valid-input-private.bin').read_bytes()
expected=(P.parent/'kernel410/tmc-source-raw-unchecked-private.bin').read_bytes()
rows=[];out=[];differing=[];nonfinite=0
for i in range(len(inputs)//288):
    actual=machine.knees(inputs[i*288:i*288+28]);out.append(actual)
    finite=all(math.isfinite(v) for v in struct.unpack('<18f',actual))
    old=bool(struct.unpack_from('<I',expected,i*340)[0])
    if not finite:nonfinite+=1
    if old and finite:
        want=expected[i*340+4:i*340+76]
        differences=[j for j in range(18) if actual[j*4:j*4+4]!=want[j*4:j*4+4]]
        if differences:differing.append(dict(index=i,fields=differences))
    else:assert old==finite,(i,'finite classification differs')
    if i%350==0:print('target knees',i+1,flush=True)
(P/'target-knees-private.bin').write_bytes(b''.join(out))
(P/'target-vs-prior-source-private.json').write_text(json.dumps(differing,indent=2)+'\n')
print(json.dumps(dict(cases=len(out),differing_finite_cases=len(differing),nonfinite_cases=nonfinite,
    first_differences=differing[:8],instructions=machine.instructions,providers=machine.providers),indent=2))
