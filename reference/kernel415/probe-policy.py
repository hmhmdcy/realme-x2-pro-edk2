"""Probe the original module policy with existing ADRC storage, no allocator stubs."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('policy415',HERE/'policy-model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);target=m.PolicyMachine()
rows=[]
for enabled in [0,1]:
    for locks in [(0,0),(1,1)]:
        r=struct.pack('<10I12f',63,enabled,62,1,1,0,*locks,1,0,*([1]*6),2,1.2,2,50,3,4)
        out,n=target.policy(r);rows.append(dict(enabled=enabled,locks=locks,out=struct.unpack('<8I6f',out),instructions=n))
(P/'probe-policy-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
