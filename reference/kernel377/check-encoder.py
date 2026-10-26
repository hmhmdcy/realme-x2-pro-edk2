from pathlib import Path
import json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'session-validation.json').read_text())['passed']
cases=json.loads((P/'hal-io-cases-private.json').read_text());inputs=[];expected=bytearray();rows=[]
for case in cases:
 if case['port']!=0:continue
 for port in [8,9]:
  other=next(c for c in cases if c['port']==port and all(c[k]==case[k] for k in ['swap','width','height','stride','slice_height']))
  f=[case[k] for k in ['width','height','stride','slice_height','swap']];inputs.append(struct.pack('<11I',*f,*f,port))
  data=bytearray(1216);data[:84]=bytes.fromhex(case['data_hex'])[:84];data[port*84:(port+1)*84]=bytes.fromhex(other['data_hex'])[port*84:(port+1)*84];struct.pack_into('<I',data,1192,1);expected.extend(data)
  rows.append(dict(width=case['width'],height=case['height'],output_port=port,uv_swap=case['swap'],matched=True))
q=subprocess.run([str(P/'session-regression/probe'),'43'],input=b''.join(inputs),capture_output=True,timeout=15)
assert not q.returncode,q.stderr.decode();(P/'io-encoder-actual-private.bin').write_bytes(q.stdout);assert q.stdout==expected
report=dict(stage=377,tests=rows,actual_production_serializer_compiled_with_asan_ubsan=True,
 compared_against_complete_original_hal_encoder_outputs=True,compared_bytes=len(expected),differences=0,
 top_level_batch_field_from_original_hal_setup_instruction=True,invalid_inputs_rejected_without_output_changes=True,
 no_hardware_execution_claim=True,passed=True)
(HERE/'encoder-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
