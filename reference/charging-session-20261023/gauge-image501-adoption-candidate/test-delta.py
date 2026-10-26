"""Actual adoption functions, synthetic postboot fixture; no network or guard."""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json,tempfile
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('adopt501',HERE/'adopt.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
device,src=m.load_device();sha=m.sha
base=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
old=json.loads((base/'eud-boot-activation/eud-boot-r2-live-001/postboot-r3-01-private/stdout-private.json').read_bytes())
raw=copy.deepcopy(old['raw']);boot='00000000-0000-0000-0000-000000000501'
for side in ['identity_before','identity_after']:
 raw[side]['boot_id']=boot;raw[side]['uname']['version']='#501 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
raw['boot_partition']['sha256']=device.CANDIDATE_BOOT;raw['logdump_partition']['sha256']=device.LOGDUMP501
raw['eud']['cmdline']+=' bq27xxx_battery.samurai_instant_current=1'
raw['gauge']={'flag':'Y','status':'Charging','current_now':'77000','current_avg':'-20000'}
raw['startup']={'sha256':'2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a','regular':True,'symlink':False,'uid':0,'mode':0o755}
raw['config_max_power_ma']='500';raw['source']['current_max']=raw['source']['input_current_limit']='500000';raw['charger']['input_current_limit']='500000'
for side in ['telemetry_before','telemetry_after']:raw[side]=raw[side].replace('budget_ua=100000','budget_ua=500000')
fixed=json.loads(src['activation_contract'])['fixed_guard_fields'];identity=raw['identity_before']
guard={**fixed,'transaction_id':'image501-test-fixture','token':'ab'*24,'boot_id':'00000000-0000-0000-0000-000000000363',
 'soc_serial_sha256':identity['serial_sha256'],'compatible_sha256':sha(base64.b64decode(identity['compatible_b64'])),
 'kernel_version':'#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026','rootfs_release_sha256':identity['rootfs']['sha256']}
camera=json.loads(Path('/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json').read_bytes())
groups=[]
with tempfile.TemporaryDirectory(prefix='image501-adoption-synthetic-') as tmp:
 tx=Path(tmp)/guard['transaction_id'];tx.mkdir();observed=tx/'postboot-fixture';observed.mkdir()
 g=json.dumps(guard).encode();(tx/'guard-private.json').write_bytes(g)
 context={'schema':'samurai-image501-fastboot-context-v1','transaction_id':guard['transaction_id'],'token':guard['token'],
  'old_boot_id':guard['boot_id'],'guard_sha256':sha(g),'files':{'guard':{'path':'guard-private.json','sha256':sha(g)}}}
 (tx/'host-context-private.json').write_text(json.dumps(context));request={'schema':'samurai-image501-postboot-readonly-v1',
  'guard':guard,'camera':camera,'context_sha256':sha((tx/'host-context-private.json').read_bytes()),'guard_sha256':sha(g),
  'new_endpoint':m.PEER,'original_key_transport_verified':True}
 def write_fixture(r):
  report={'schema':request['schema'],'transaction_id':guard['transaction_id'],'context_sha256':request['context_sha256'],
   'guard_sha256':request['guard_sha256'],'raw':r,'result':{'passed':True}}
  (observed/'stdout-private.json').write_text(json.dumps(report))
  (observed/'receiver-result-private.json').write_text(json.dumps({'passed':True,'transport_exit':0}))
  prefix='POSTBOOT_REQUEST=__import__("json").loads(__import__("base64").b64decode('+repr(base64.b64encode(json.dumps(request).encode()).decode())+'))\n'
  (observed/'executed-device-source.py').write_bytes(prefix.encode()+src['postboot_device'])
 write_fixture(raw);d,s=m.review(tx/'host-context-private.json',observed)
 assert d['version']==identity['uname']['version'] and d['version'].startswith('#501 ')
 assert d['candidate_logdump_sha256']==device.LOGDUMP501 and d['guard'].endswith('image501-test-fixture-adopted/boot-id-private.txt')
 code=m.payload(d,s);compile(code,'actual-adoption-payload','exec')
 assert b'/dev/mem' not in code and b'mmap' not in code
 groups.append('actual review reaudits new501/fullpair/flagY/500 and uses actual new version; payload source compiles')
 for label,edit in [('mixed pair',lambda r:r['logdump_partition'].update(sha256='0'*64)),('flag false',lambda r:r['gauge'].update(flag='N')),('old version',lambda r:r['identity_before']['uname'].update(version='#363 old'))]:
  bad=copy.deepcopy(raw);edit(bad);write_fixture(bad)
  try:m.review(tx/'host-context-private.json',observed)
  except AssertionError:pass
  else:raise AssertionError(label+' accepted')
 groups.append('passed labels cannot bypass actual mixedpair/flag/version checks')
 write_fixture(raw);out=tx/'adoption-fixture';out.mkdir();pointer=Path(tmp)/'boot-adoption-private.json'
 before=b'{"old":"pointer"}';pointer.write_bytes(before);(out/'boot-adoption-before-image501-private.json').write_bytes(before)
 reply={'guard_created':True,'old_guards_preserved':True,'transaction_id':d['transaction_id'],'boot_id':d['boot'],'guard':d['guard'],
  'candidate_pair_verified':True,'postboot_raw_sha256':d['postboot_raw_sha256'],'fresh_validation_passed':True}
 with patch.object(m,'BASE',Path(tmp)):
  result=m.publish(tx,out,d,reply)
 assert (out/'boot-adoption-before-image501-private.json').read_bytes()==before and json.loads(pointer.read_bytes())==result
 assert result['candidate_logdump_sha256']==device.LOGDUMP501 and result['Image501_verified']
 assert json.loads((out/'new-endpoint-private.json').read_bytes())['observed_new_boot']==boot
 groups.append('actual publish preserves old backup then atomic pointer, new endpoint bound to synthetic newboot only in temp fixture')
result={'passed':True,'groups':groups,'fixtures_are_synthetic_not_runtime_pins':True,'no_network_device_or_remote_guard':True,
 'files':{n:sha((HERE/n).read_bytes()) for n in ['adopt.py','source-pins.json','test-delta.py']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'groups':len(groups),'synthetic_only':True}))
