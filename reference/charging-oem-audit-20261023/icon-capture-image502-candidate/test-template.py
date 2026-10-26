"""502 identity delta only; temporary synthetic evidence, never a real runtime pin."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,tempfile
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/icon-capture-image501-candidate'

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

m=module('icon502_template',HERE/'launcher.py');b=module('icon502_bind_actual',HERE/'bind-identity.py')
sha=m.sha;groups=[];cases=0
def rejects(call):
 try:call()
 except (AssertionError,ValueError,FileNotFoundError):return
 raise AssertionError('required refusal missing')
def functions(path):
 text=path.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}

for n in ['worker.py','audit.py','baseline-test-result.json']:assert (HERE/n).read_bytes()==(OLD/n).read_bytes()
assert (HERE/'capture-entry.py').read_bytes().replace(b'/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt',b'/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt')==(OLD/'capture-entry.py').read_bytes()
oldf,newf=functions(OLD/'launcher.py'),functions(HERE/'launcher.py')
unchanged={n:sha(s.encode()) for n,s in oldf.items() if newf.get(n)==s}
assert all(n in unchanged for n in ['ready_check','retain_fetch','cleanup_check','save_new','runtime_expected','transport','main'])
old=module('old501_icon_only',OLD/'launcher.py')
assert m.REMOTE.replace('/icon-capture-image502','/icon-capture-image501')==old.REMOTE
assert functions(HERE/'bind-identity.py')['bind']==functions(OLD/'bind-identity.py')['bind']
groups.append('frozen worker/audit/32 receipt exact; entry only guard; heartbeat130/settle90/stop/join/fetch semantics unchanged')

with tempfile.TemporaryDirectory(prefix='icon502-profile-fixture-') as tmp:
 root=Path(tmp);pins=root/'pins.json';boot='00000000-0000-0000-0000-000000000502'
 guard='/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'
 identity={'boot_id':boot,'uname':{'version':'#502 reproducible-fixture'}}
 post={'schema':'samurai-image502-notify-postboot-readonly-v1','raw':{'boot_partition':{'sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'},
  'logdump_partition':{'sha256':'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'},'identity_before':identity,'identity_after':identity},
  'result':{'passed':True,'checks':{'R8_install':{'R8_disk_and_live_notes':True},'camera481':{'camera481_files_packages_notes':True},
  'EUD_producers':{'DT_disabled_no_EUD_cmdline_or_active_producer':True},'instant_gauge':{'flag_Y_and_exact_cmdline':True,'startup500_descriptor_and_native500_preserved':True,
  'source_type':'CDP','source_budget_ua':1500000,'hardware_input_ua':900000,'SDP_hardware500_observed':False}}}}
 docs={'postboot':post,'adoption':{'Image502_verified':True,'original_key_verified':True,'baseline481_verified':True,'charging_manifest_sha256':m.MANIFEST,
  'candidate_boot_sha256':post['raw']['boot_partition']['sha256'],'candidate_logdump_sha256':post['raw']['logdump_partition']['sha256'],'guard_path':guard},
  'adopt_request':{'manifest':m.MANIFEST,'candidate_boot_sha256':post['raw']['boot_partition']['sha256'],'candidate_logdump_sha256':post['raw']['logdump_partition']['sha256'],
   'boot':boot,'guard':guard,'release':'same-k363-release','version':identity['uname']['version'],'rootfs':'fixture','notes':{}},
  'adopt_result':{'passed':True,'guard_created':True,'old_guards_preserved':True,'old_pointer_backup_preserved':True},
  'receiver':{'passed':True,'transport_exit':0},'endpoint':{'kind':'usb-ipv6','original_key_verified':True,'postboot_Image502_passed':True,
   'host_key_alias':'169.254.42.1','interface_index':29,'peer':'fe80::62:bcff:fe28:a101%29','observed_new_boot':boot,'guard_path':guard}}
 def fixture(d):
  for n,value in d.items():(root/(n+'.json')).write_text(json.dumps(value))
  digest=sha((root/'postboot.json').read_bytes())
  for n in ['adoption','adopt_request']:
   value=json.loads((root/(n+'.json')).read_bytes());value['postboot_raw_sha256']=digest;(root/(n+'.json')).write_text(json.dumps(value))
  entries={n:{'path':str(root/(n+'.json')),'sha256':sha((root/(n+'.json')).read_bytes())} for n in d}
  entries['transport']={'path':str(HERE/'transport.py'),'sha256':sha((HERE/'transport.py').read_bytes())}
  key=REF/'kernel184/host.py';entries['key_transport']={'path':str(key),'sha256':sha(key.read_bytes())}
  pins.write_text(json.dumps(entries));return entries
 fixture(docs);assert m.reviewed_identity(pins)[:2]==(boot,guard);cases+=1
 sdp=copy.deepcopy(docs);sdp['postboot']['result']['checks']['instant_gauge'].update(source_type='SDP',source_budget_ua=500000,hardware_input_ua=500000,SDP_hardware500_observed=True)
 fixture(sdp);assert m.reviewed_identity(pins)[:2]==(boot,guard);cases+=1
 fixture(docs);assert m.runtime_expected(pins)['version'].startswith('#502 ')
 for label,edit in [('old501 version',lambda d:d['adopt_request'].update(version='#501 old')),
  ('old501 flag',lambda d:(d['adoption'].pop('Image502_verified'),d['adoption'].update(Image501_verified=True))),
  ('old501 schema',lambda d:d['postboot'].update(schema='samurai-image501-postboot-readonly-v1')),
  ('oldlogdump',lambda d:d['postboot']['raw']['logdump_partition'].update(sha256='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9')),
  ('changedboot',lambda d:d['postboot']['raw']['boot_partition'].update(sha256='0'*64)),
  ('oldguard',lambda d:d['adopt_request'].update(guard='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt')),
  ('postboot not passed',lambda d:d['postboot']['result'].update(passed=False)),
  ('adoption not passed',lambda d:d['adopt_result'].update(passed=False)),
  ('oldendpoint',lambda d:(d['endpoint'].pop('postboot_Image502_passed'),d['endpoint'].update(postboot_Image501_passed=True)))]:
  bad=copy.deepcopy(docs);edit(bad);fixture(bad);rejects(lambda:m.reviewed_identity(pins));cases+=1
 groups.append('actual profile permits SDP/CDP metadata; rejects old501 schema/version/guard/flag/endpoint, mixed payload and missing passed evidence')
 # Actual bind() runs only inside a new temporary directory. Its one hardcoded
 # pointer path is redirected to this fixture, so the current global pointer is
 # never read. Migration receipt checks still execute via the real adopt_local.
 migration=root/'migration-fixture.json'
 receipt={'schema':'charging-icon-image502-template-tests-v1','passed':True,'runtime_identity_unbound':True,
  'launcher_sha256':sha((HERE/'launcher.py').read_bytes()),'sha256':m.FROZEN,'manifest_sha256':m.MANIFEST,
  'files':{n:sha((HERE/n).read_bytes()) for n in ['launcher.py','capture-entry.py','transport.py','bind-identity.py','test-template.py']}}
 migration.write_text(json.dumps(receipt))
 for label,qualify in [('failed',False),('passed',True)]:
  work=root/label;work.mkdir();adoption=work/'adoption-01-private';adoption.mkdir();observed=work/'postboot';observed.mkdir()
  data=copy.deepcopy(docs);data['adopt_result']['passed']=qualify;fixture(data)
  for n,target in [('adoption','pointer.json'),('adopt_request','adopt-request-private.json'),('adopt_result','adoption-result-private.json'),('endpoint','new-endpoint-private.json')]:
   (work/target if n=='adoption' else adoption/target).write_bytes((root/(n+'.json')).read_bytes())
  for n,target in [('postboot','stdout-private.json'),('receiver','receiver-result-private.json')]:
   (observed/target).write_bytes((root/(n+'.json')).read_bytes())
  runtime=adoption/'icon-identity-pins-private.json';original=b.m.adopt_local
  def map_path(value):
   if str(value)=='/mnt/e/edk2-samurai-out/charging-management-20261023/boot-adoption-private.json':return work/'pointer.json'
   return Path(value)
  with patch.object(b,'Path',side_effect=map_path),patch.object(b.m,'PINS',runtime),patch.object(b.m,'adopt_local',side_effect=lambda **kw:original(pins=kw['pins'],migration=migration)):
   if qualify:assert b.bind(adoption,observed)['bound_actual_identity'] and runtime.exists()
   else:rejects(lambda:b.bind(adoption,observed));assert not runtime.exists()
  cases+=1
 groups.append('actual bind atomically publishes only qualified temporary pins and refuses unpassed adoption; real pointer/pins untouched')
rejects(lambda:m.reviewed_identity(pins=Path('/nonexistent/offline-image502-pins.json')));cases+=1
result={'schema':'charging-icon-image502-template-tests-v1','passed':True,'runtime_identity_unbound':True,'groups':groups,
 'affected_cases':cases,'unchanged_actual_launcher_functions':unchanged,
 'launcher_sha256':sha((HERE/'launcher.py').read_bytes()),'sha256':m.FROZEN,'manifest_sha256':m.MANIFEST,
 'files':{n:sha((HERE/n).read_bytes()) for n in ['launcher.py','capture-entry.py','transport.py','bind-identity.py','test-template.py']},
 'reused_501_template_receipt_sha256':sha((OLD/'template-test-result.json').read_bytes()),
 'fixtures_synthetic_no_real_identity_pins':True,'old32_and12_not_rerun':True,'network_device_global_pointer_accessed':False}
(HERE/'template-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'groups':len(groups),'affected_cases':cases,'runtime_pins_created':False,'old_suites_not_rerun':True}))
