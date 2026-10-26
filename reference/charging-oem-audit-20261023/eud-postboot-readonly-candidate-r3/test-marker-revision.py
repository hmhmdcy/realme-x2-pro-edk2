"""Actual decoder only; no collection, OS/device access or old suite."""
from pathlib import Path
import base64,hashlib,json,struct
HERE=Path(__file__).resolve().parent;R2=HERE.parent/'eud-postboot-readonly-candidate-r2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 env={'__name__':'offline_decoder_function_definitions'}
 exec(compile(path.read_text(),str(path),'exec'),env)
 return env
new,old=load(HERE/'device.py'),load(R2/'device.py')
def ring(text):
 data=text.encode();size=0x14000-32;fields=[0x474f4c45,0x10000,size,len(data),0,0,0,0]
 raw=struct.pack('<8I',*fields)+data+bytes(size-len(data))
 return dict(raw_b64=base64.b64encode(raw).decode(),header_before=fields,header_after=fields,header_stable=True)
valid='[SAMURAI-EUD-OFF] attempted=1 write=1 arm=01010101 before=01010101 after=00000000 status=Success\n'
cases=[('one complete off report',valid,True,1),
 ('valid plus truncated second prefix',valid+'[SAMURAI-EUD-OFF] attempted=1 write=',False,2),
 ('valid plus malformed second prefix',valid+'[SAMURAI-EUD-OFF] not-a-complete-report\n',False,2),
 ('valid plus missing-close prefix',valid+'[SAMURAI-EUD-OFF',False,2),
 ('valid plus prefixed malformed record',valid+'DEBUG: [SAMURAI-EUD-OFF] incomplete\n',False,2),
 ('unrelated retained text plus valid report','private unrelated text\n'+valid,True,1)]
rows=[]
for label,text,want,count in cases:
 result=new['decode_ring'](ring(text))
 assert result['ready'] is want and result['marker_prefix_count']==count,label
 assert result['receipts']==[valid.rstrip('\n')],label
 assert result['callback_success_independently_proven'] is False
 rows.append(dict(label=label,ready=result['ready'],marker_prefix_count=result['marker_prefix_count'],public_complete_receipts=len(result['receipts'])))
assert old['decode_ring'](ring(cases[1][1]))['ready'] is True
assert old['decode_ring'](ring(cases[2][1]))['ready'] is True
source=json.loads((HERE/'revision-source-result.json').read_bytes())
assert sha(R2/'test-full-result.json')==source['R2_full_result_sha256']
result=dict(passed=True,cases=rows,case_count=len(rows),actual_R2_ambiguous_prefix_accepted=True,
 tested_files={n:sha(HERE/n) for n in ['device.py','device-body.py','test-marker-revision.py','r2-to-r3.patch']},
 only_actual_function_executed='decode_ring',R2_full_11_cases_reused=True,
 R1_other_9_groups_reused=True,old_suites_rerun=False,device_accessed=False,
 R2_full_result_sha256=source['R2_full_result_sha256'],R1_other_groups_receipt_sha256=source['R1_other_groups_receipt_sha256'])
(HERE/'test-marker-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=len(rows),old_suites_rerun=False,device_accessed=False)))
