"""Compare current portable generation with three retained target probes."""
from pathlib import Path
import importlib.util,json,math,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('generation413',HERE/'generation-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);machine=k.GenerationMachine()
weights=bytes(machine.u.mem_read(0xdb39c,4096));assert all(math.isfinite(x) for x in struct.unpack('<1024f',weights))
(P/'histogram-log-weights-private.bin').write_bytes(weights)
region=(P/'probe-region-private.bin').read_bytes();gamma=(P/'probe-gamma-private.bin').read_bytes()
records=[];expected=[]
for kind,hist in [('none',None),('uniform',struct.pack('<1024I',*([64]*1024))),('black',struct.pack('<1024I',65536,*([0]*1023)))]:
    records.append(region+struct.pack('<2fI',2,1.2,hist is not None)+gamma+weights+(hist if hist is not None else bytes(4096)))
    raw=(P/(kind+'-adrc-private.bin')).read_bytes();proc=(P/(kind+'-processed-hist-private.bin')).read_bytes()
    out=raw[16:56]+raw[92:128]+raw[64:68]+raw[4228:4236]+raw[56:64]+proc+raw[128:4224]
    assert len(out)==8288
    finite=all(math.isfinite(v) for v in struct.unpack('<2072f',out))
    expected.append(struct.pack('<I',finite)+(out if finite else bytes([0xa5])*8288))
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(HERE/'generation-runner.cpp'),str(HERE/'libipa/tmc11_generation.cpp'),'-o',str(P/'generation-host')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(P/'generation-host')],input=b''.join(records),capture_output=True);assert not q.returncode,q.stderr.decode()
actual=q.stdout;wanted=b''.join(expected);assert len(actual)==len(wanted)
(P/'probe-port-actual-private.bin').write_bytes(actual);(P/'probe-target-expected-private.bin').write_bytes(wanted)
rows=[]
for i,kind in enumerate(['none','uniform','black']):
    left=actual[i*8292:(i+1)*8292];right=wanted[i*8292:(i+1)*8292]
    locations=[j for j in range(2072) if left[4+j*4:8+j*4]!=right[4+j*4:8+j*4]]
    rows.append(dict(kind=kind,actual_ok=struct.unpack_from('<I',left)[0],different_bytes=sum(a!=b for a,b in zip(left,right)),different_float_fields=len(locations),first_fields=locations[:20]))
print(json.dumps(rows,indent=2))
