from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('decoder372',HERE/'decode-ramoops.py');decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
profile=json.loads((HERE/'firmware-context-validation.json').read_text());rows=[]
for kind in ['data','prefetch']:
 values=json.loads((P/('synthetic-'+kind+'-snapshot-private.json')).read_text());lines=['A5 pre-reset snapshot begin ranges=4','A5 pre-reset snapshot code-match=1']
 for window in profile['windows']:
  for j in range(0,window['words'],8):
   n=min(8,window['words']-j);base=window['offset']+4*j;words=[values[str(base+4*i)] if i<n else 0 for i in range(8)]
   lines.append('A5 pre-reset snapshot data offset='+format(base,'x')+' count='+str(n)+' values='+','.join(format(w,'08x') for w in words))
 lines.append('A5 pre-reset snapshot end');raw='\n'.join(lines)+'\n';result=decoder.decode(raw,profile)
 assert result['exception_type']==(3 if kind=='data' else 1) and result['fault_pc'] is None and result['stack_pc_candidate']==0x24a0c and result['context_pointer_matches_original']
 rows.append(dict(case=kind,passed=True))
 # Model the original C formatting provider separately; its stack push may
 # overwrite the old popped-PC word. This does not execute snprintf itself.
 prefix='Data' if kind=='data' else 'Prefetch'
 message=(prefix+' Abort Exception at 0x24a0c, FSR=0x805 FAR=0x10a00000').encode()+b'\0'
 window=next(w for w in profile['windows'] if w['role']=='original-abort-stack-tail')
 import struct
 stack=bytearray().join(struct.pack('<I',values[str(window['offset']+4*i)]) for i in range(window['words']))
 stack[8:8+len(message)]=message
 for i in range(window['words']):values[str(window['offset']+4*i)]=struct.unpack_from('<I',stack,i*4)[0]
 values[str(result['saved_abt_sp']+32)]=0x28424
 def formatted():
  lines=['A5 pre-reset snapshot begin ranges=4','A5 pre-reset snapshot code-match=1']
  for w in profile['windows']:
   for j in range(0,w['words'],8):
    n=min(8,w['words']-j);base=w['offset']+4*j;words=[values[str(base+4*i)] if i<n else 0 for i in range(8)]
    lines.append('A5 pre-reset snapshot data offset='+format(base,'x')+' count='+str(n)+' values='+','.join(format(v,'08x') for v in words))
  return '\n'.join(lines+['A5 pre-reset snapshot end'])
 formatted_result=decoder.decode(formatted(),profile)
 assert formatted_result['fault_pc']==0x24a0c and formatted_result['stack_pc_candidate']==0x28424
 rows.append(dict(case=kind+'-formatted-pc',passed=True))
 stack[8:8+len(message)]=message.replace(b'FSR=0x805',b'FSR=0x806')
 for i in range(window['words']):values[str(window['offset']+4*i)]=struct.unpack_from('<I',stack,i*4)[0]
 assert decoder.decode(formatted(),profile)['fault_pc'] is None
 rows.append(dict(case=kind+'-formatted-fsr-mismatch',passed=True))
 bad=[raw.replace('code-match=1','code-match=0'),raw.rsplit('A5 pre-reset snapshot end',1)[0],raw.replace(lines[2]+'\n',''),raw.replace(lines[2],lines[2]+'\n'+lines[2]),raw.replace('count=3','count=9'),raw.replace('offset=1099a0','offset=ffffffff')]
 for i,text in enumerate(bad):
  try:decoder.decode(text,profile)
  except ValueError:rows.append(dict(case=kind+'-bad-'+str(i),passed=True))
  else:raise AssertionError('Malformed snapshot accepted')
report=dict(stage=372,strict_actual_decoder=True,tests=rows,inputs_from_executed_oem_abort_context_instruction_tests=True,
 rejects_code_mismatch_missing_duplicate_out_of_profile_and_bad_rows=True,does_not_infer_pc_from_wrong_context_pointer=True,
 synthetic_instruction_records_not_target_fault_or_ramoops_proof=True,phone_operations=False,passed=True)
(HERE/'decoder-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
