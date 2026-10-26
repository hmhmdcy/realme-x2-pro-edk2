"""Actual 502 review/publish/previous-pointer gates in temporary fixtures only."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys,tempfile
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;POST=HERE.parent/'image502-postboot-readonly';sys.path.insert(0,str(POST))
import fixture as f
m=f.module('adopt502',HERE/'adopt.py');p=f.module('payload_for_adopt502',POST/'payload.py')
cases=[]
def reject(call):
 try:call()
 except (AssertionError,ValueError,KeyError):return
 raise AssertionError('required refusal missing')
r=f.facts()
with tempfile.TemporaryDirectory(prefix='image502-adoption-fixture-') as tmp:
 context,guard,c=f.context_fixture(tmp,r);observed=context.parent/'postboot-fixture'
 request=p.make_request(context,'/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json',m.PEER,True,True)
 f.receiver_fixture(observed,request,r,(POST/'device.py').read_bytes())
 d,src=m.review(context,observed)
 assert d['guard']=='/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'
 assert d['candidate_boot_sha256']==guard['unchanged_boot_sha256'] and d['candidate_logdump_sha256']==guard['candidate_logdump_sha256']
 code=m.payload(d,src);compile(code,'actual502-adopt-payload','exec');assert b'/dev/mem' not in code and b'mmap' not in code
 cases.append('actual review reaudits real502 contract and newboot with boot unchanged and only logdump replaced')
 report=json.loads((observed/'stdout-private.json').read_bytes())
 for label,change in [('old501',lambda x:x['raw']['identity_before']['uname'].__setitem__('version','#501 old')),('sameboot',lambda x:x['raw']['identity_before'].__setitem__('boot_id',guard['boot_id'])),('oldlogdump',lambda x:x['raw']['logdump_partition'].__setitem__('sha256',guard['rollback_logdump_sha256'])),('changedboot',lambda x:x['raw']['boot_partition'].__setitem__('sha256','0'*64))]:
  bad=copy.deepcopy(report);change(bad);(observed/'stdout-private.json').write_text(json.dumps(bad));reject(lambda:m.review(context,observed));cases.append('passed_receiver_cannot_adopt_'+label)
 (observed/'stdout-private.json').write_text(json.dumps(report))
 previous={'guard_path':guard['old_boot_guard_path'],'Image501_verified':True,'original_key_verified':True,
  'candidate_boot_sha256':guard['unchanged_boot_sha256'],'candidate_logdump_sha256':guard['rollback_logdump_sha256'],'charging_manifest_sha256':d['manifest']}
 m.check_previous(previous,d)
 for name,value in [('guard_path',d['guard']),('Image501_verified',False),('candidate_boot_sha256','0'*64),('candidate_logdump_sha256',d['candidate_logdump_sha256'])]:
  reject(lambda:m.check_previous({**previous,name:value},d));cases.append('previous_pointer_reject_'+name)
 out=context.parent/'adoption-fixture';out.mkdir();pointer=Path(tmp)/'boot-adoption-private.json'
 before=json.dumps(previous).encode();pointer.write_bytes(before);(out/'boot-adoption-before-image502-private.json').write_bytes(before)
 reply={'guard_created':True,'old_guards_preserved':True,'transaction_id':d['transaction_id'],'boot_id':d['boot'],'guard':d['guard'],
  'boot_and_logdump_verified':True,'postboot_raw_sha256':d['postboot_raw_sha256'],'fresh_validation_passed':True}
 with patch.object(m,'BASE',Path(tmp)):
  pointer.write_bytes(b'{"another_owner":true}');reject(lambda:m.publish(context.parent,out,d,reply));assert not (out/'new-endpoint-private.json').exists()
  pointer.write_bytes(before);published=m.publish(context.parent,out,d,reply)
 assert (out/'boot-adoption-before-image502-private.json').read_bytes()==before
 assert json.loads(pointer.read_bytes())==published and published['Image502_verified'] and not published.get('Image501_verified')
 endpoint=json.loads((out/'new-endpoint-private.json').read_bytes())
 assert endpoint['postboot_Image502_passed'] and endpoint['observed_new_boot']==f.NEWBOOT and endpoint['guard_path']==d['guard']
 cases.append('actual publish rejects concurrent pointer change then preserves backup and atomically publishes unique502 guard and endpoint')
old=(HERE.parents[1]/'charging-session-20261023/gauge-image501-adoption-candidate/adopt.py').read_text();new=(HERE/'adopt.py').read_text()
def functions(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
oldf,newf=functions(old),functions(new)
unchanged={n:f.sha(s.encode()) for n,s in oldf.items() if newf.get(n)==s}
assert set(unchanged)=={'create','save','sources','main'}
def join_tail(text):return text.split(" with (out/'adopt-stdout-private.json').open('xb') as stdout",1)[1].split(" reply=json.loads",1)[0]
assert join_tail(old)==join_tail(new)
result={'passed':True,'affected_case_count':len(cases),'cases':cases,'tested_files':{n:f.sha((HERE/n).read_bytes()) for n in ['adopt.py','source-pins.json','test-delta.py']},
 'unchanged_functions':unchanged,'unchanged_actual_same_child_join_sha256':f.sha(join_tail(new).encode()),
 'reused_receipts':{n:f.sha((HERE.parents[1]/('charging-session-20261023/gauge-image501-adoption-candidate/'+n)).read_bytes()) for n in ['test-result.json','test-optimize-result.json','test-cdp-binding-result.json']},
 'source_device_sha256':f.sha((POST/'device.py').read_bytes()),'fixture_is_synthetic_not_real502':True,
 'old_suites_rerun':False,'device_SSH_USB_prepare_adoption_global_pointer_access':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'affected_cases':len(cases)}))
