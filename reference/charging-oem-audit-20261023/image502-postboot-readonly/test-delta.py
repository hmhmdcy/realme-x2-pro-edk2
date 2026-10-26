"""Changed identity/context/partition functions only; no transport or device."""
from pathlib import Path
import ast,copy,hashlib,json,tempfile
import fixture as f
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
m=f.module('postboot502',HERE/'device.py');p=f.module('payload502',HERE/'payload.py')
cases=[]
def reject(call):
 try:call()
 except (AssertionError,ValueError,KeyError):return
 raise AssertionError('required refusal missing')
def functions(path):
 text=path.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
r=f.facts()
with tempfile.TemporaryDirectory(prefix='image502-postboot-fixture-') as tmp:
 context,guard,c=f.context_fixture(tmp,r)
 request=p.make_request(context,'/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json','fe80::62:bcff:fe28:a101%29',True,True)
 assert request['guard']['partitions']==['logdump'] and 'candidate_boot_sha256' not in request['guard']
 assert m.check_identity(r['identity_before'],guard)['new_boot']
 assert m.check_partitions(r)['unchanged_boot_exact']
 code=p.make_payload(request);compile(code,'actual502-payload','exec')
 assert m.audit(r,request)['passed'];cases.append('actual seven-raw 502 context plus unchanged97811/newace2/newboot502/CDP Full audit')
 for label,field,value in [('old501','version','#501 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'),('sameboot','boot_id',guard['boot_id'])]:
  bad=copy.deepcopy(r['identity_before'])
  (bad['uname'] if field=='version' else bad)[field]=value
  reject(lambda:m.check_identity(bad,guard));cases.append('reject_'+label)
 for field,value in [('boot_partition','4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'),('logdump_partition','7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9')]:
  bad=copy.deepcopy(r);bad[field]['sha256']=value;reject(lambda:m.check_partitions(bad));cases.append('reject_changed_'+field)
 original=context.read_bytes();bad=dict(c,schema='samurai-image501-fastboot-context-v1');context.write_text(json.dumps(bad))
 reject(lambda:p.make_request(context,'/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json','fe80::62:bcff:fe28:a101%29',True,True));context.write_bytes(original)
 cases.append('reject501_context_even_if_guard_from_new_profile')
 reject(lambda:p.make_request(context,'/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json','169.254.42.1',True,True));cases.append('reject_unobserved_transport_peer')
 # Retain existing real CDP/Full semantics and separate NOW/AVG. No forced Charging.
 assert m.check_gauge(r)['source_type']=='CDP' and m.check_charging(r)['ready']
 sdp=copy.deepcopy(r);sdp['source']['usb_type']='Unknown [SDP] DCP CDP C';sdp['source']['current_max']='500000';sdp['charger']['input_current_limit']='500000'
 for side in ('telemetry_before','telemetry_after'):sdp[side]=sdp[side].replace('budget_ua=1500000','budget_ua=500000')
 assert m.check_gauge(sdp)['source_type']=='SDP' and m.check_charging(sdp)['ready'];cases.append('unchanged_actual_SDP500_and_CDP1500_Full_FC_signs_preserved')
old=functions(REF/'charging-management-20261023/image501-postboot-readonly/device.py');new=functions(HERE/'device.py')
unchanged={n:hashlib.sha256(s.encode()).hexdigest() for n,s in old.items() if n in new and s==new[n]}
assert set(old)-set(unchanged)=={'check_identity','check_partitions','main'}
assert functions(REF/'charging-management-20261023/image501-postboot-readonly/payload.py')['save_response']==functions(HERE/'payload.py')['save_response']
result={'passed':True,'affected_case_count':len(cases),'cases':cases,'unchanged_device_functions':unchanged,
 'tested_files':{n:f.sha((HERE/n).read_bytes()) for n in ['device.py','payload.py','source-pins.json','fixture.py','test-delta.py']},
 'fixture_source_sha256':f.sha(f.ORIGINAL.read_bytes()),'synthetic_new_identity_not_runtime_guard':True,
 'reused_receipts':{'original_postboot':f.sha((REF/'charging-management-20261023/image501-postboot-readonly/test-result.json').read_bytes())},
 'old_suites_rerun':False,'device_SSH_USB_build_Git':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'affected_cases':len(cases),'unchanged_functions':len(unchanged)}))
