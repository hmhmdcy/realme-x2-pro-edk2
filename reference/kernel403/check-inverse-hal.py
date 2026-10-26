"""Compare portable/source inverse tables to actual factory HAL instructions."""
from pathlib import Path
import importlib.util,json,struct,sys,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('ltm403',HERE/'ltm-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);model=m.LTM()
raw=(P.parent/'kernel352/inverse-oracle-input-private.bin').read_bytes();expected=(P.parent/'kernel352/inverse-oracle-output-private.bin').read_bytes();assert len(raw)==29*128 and len(expected)==29*256
count=int(sys.argv[1]) if len(sys.argv)>1 else 29;assert 0<count<=29;start=time.monotonic();actual=[];rows=[]
for i in range(count):
 nodes=struct.unpack_from('<64H',raw,i*128);before=model.instructions;out=model.inverse(nodes);assert out==expected[i*256:(i+1)*256],('original HAL mismatch',i,sum(a!=b for a,b in zip(out,expected[i*256:(i+1)*256])))
 hit=model.inverse(nodes,cached=True);assert hit==out;actual.append(out);rows.append(dict(index=i,miss_and_hit_instructions=model.instructions-before,bytes=256,different_bytes=0,passed=True));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=403,cases=count,original_inlined_inverse_gamma_fragment_executed=True,range=['0x3618a4','0x362320'],cache_hit_and_miss_each_case=True,compared_bytes=256*count,different_bytes=0,source_reference_and_portable_host_aarch64_352_reused=True,providers=model.providers,original_instructions=model.instructions,seconds=round(time.monotonic()-start,2),phone_accessed=False,passed=True)
(P/('inverse-hal-'+str(count)+'-private.bin')).write_bytes(b''.join(actual));(HERE/('inverse-hal-'+str(count)+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
