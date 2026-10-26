"""Append newly required degeneracy cases without repeating retained target runs."""
from pathlib import Path
import importlib.util,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('generation413',HERE/'generation-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.GenerationMachine()
report=json.loads((HERE/'generation-validation.json').read_text());assert report['cases']==152 and report['passed']
inputs=(P/'generation-input-private.bin').read_bytes();wanted=(P/'generation-expected-private.bin').read_bytes()
valid=(P/'generation-valid-input-private.bin').read_bytes();expected=(P/'generation-target-expected-private.bin').read_bytes()
raw=(P/'generation-target-raw-private.bin').read_bytes();meta=json.loads((P/'generation-cases-private.json').read_text())
fields=list(struct.unpack_from('<44f',valid));fields[30:35]=[0,1,1,1,0];fields[37:39]=[.5,.5]
region=struct.pack('<44f',*fields);gamma=(P/'target-default-gamma-private.bin').read_bytes();weights=(P/'histogram-log-weights-private.bin').read_bytes()
new_records=[];new_expected=[];new_raw=[];finite_count=0
for hist in [None,bytes(4096),struct.pack('<1024I',*([64]*1024)),struct.pack('<1024I',65536,*([0]*1023))]:
    result=target.generate(region,struct.pack('<2f',2,1.2),gamma,hist);a=result['adrc']
    out=a[16:56]+a[92:128]+a[64:68]+a[4228:4236]+a[56:64]+result['processed_hist']+a[128:4224]
    finite=all(math.isfinite(v) for v in struct.unpack('<2072f',out));finite_count+=finite
    new_records.append(region+struct.pack('<2fI',2,1.2,hist is not None)+gamma+weights+(hist if hist is not None else bytes(4096)))
    new_raw.append(out);new_expected.append(struct.pack('<I',finite)+(out if finite else bytes([0xa5])*8288))
    meta.append(dict(kind='synthetic-histogram-only-degenerate',source_bindings=[],target_instructions=result['instructions']))
(P/'generation-valid-input-private.bin').write_bytes(valid+b''.join(new_records))
(P/'generation-target-expected-private.bin').write_bytes(expected+b''.join(new_expected))
(P/'generation-target-raw-private.bin').write_bytes(raw+b''.join(new_raw))
(P/'generation-input-private.bin').write_bytes(valid+b''.join(new_records)+inputs[152*9408:])
(P/'generation-expected-private.bin').write_bytes(expected+b''.join(new_expected)+wanted[152*8292:])
(P/'generation-cases-private.json').write_text(json.dumps(meta,indent=2)+'\n')
report['cases']+=4;report['synthetic_histogram_gamma_and_gain_cases']+=4
report['finite_target_results']+=finite_count;report['nonfinite_target_result_cases']+=4-finite_count
report['target_instructions']+=target.instructions
for name,n in target.providers.items():report['target_providers'][name]=report['target_providers'].get(name,0)+n
report.update(architectures=[],new_degenerate_target_cases_appended_without_repeating_previous_runs=True,passed=False)
(HERE/'generation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(new_cases=4,new_finite_cases=finite_count,target_instructions=target.instructions)))
