"""Only new profile fields; synthetic local fixtures, no old32/12 suites."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent
OLD=HERE.parents[1]/'charging-oem-audit-20261023/icon-capture-r8-eud-off-candidate'
spec=importlib.util.spec_from_file_location('icon501_template',HERE/'launcher.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=m.sha;groups=[]
for n in ['worker.py','audit.py','baseline-test-result.json']:assert (HERE/n).read_bytes()==(OLD/n).read_bytes()
assert (HERE/'capture-entry.py').read_bytes().replace(b'/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt',b'/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt')==(OLD/'capture-entry.py').read_bytes()
def fn(path,name):
 text=path.read_text();return ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name))
for n in ['ready_check','retain_fetch','cleanup_check','save_new']:
 assert fn(HERE/'launcher.py',n)==fn(OLD/'launcher.py',n)
oldspec=importlib.util.spec_from_file_location('old_icon_source_only',OLD/'launcher.py');old=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(old)
assert m.REMOTE.replace('/icon-capture-image501','/icon-capture-r8-eud-off')==old.REMOTE
groups.append('worker/audit/history bytes unchanged; CaptureCycle90/current_avg adapter only guard literal; ready/remote lifecycle preserved')
with tempfile.TemporaryDirectory(prefix='icon501-synthetic-profile-') as tmp:
 root=Path(tmp);pins=root/'pins.json';boot='00000000-0000-0000-0000-000000000501'
 guard='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
 identity={'boot_id':boot,'uname':{'version':'#501 reproducible-fixture'}}
 post={'schema':'samurai-image501-postboot-readonly-v1','raw':{'boot_partition':{'sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'},
  'logdump_partition':{'sha256':'7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'},'identity_before':identity,'identity_after':identity},
  'result':{'passed':True,'checks':{'R8_install':{'R8_disk_and_live_notes':True},'camera481':{'camera481_files_packages_notes':True},
  'EUD_producers':{'DT_disabled_no_EUD_cmdline_or_active_producer':True},'instant_gauge':{'flag_Y_and_exact_cmdline':True,'startup500_descriptor_and_native500_preserved':True}}}}
 docs={'postboot':post,'adoption':{'Image501_verified':True,'original_key_verified':True,'baseline481_verified':True,'charging_manifest_sha256':m.MANIFEST,
  'candidate_boot_sha256':post['raw']['boot_partition']['sha256'],'candidate_logdump_sha256':post['raw']['logdump_partition']['sha256'],'guard_path':guard},
  'adopt_request':{'manifest':m.MANIFEST,'candidate_boot_sha256':post['raw']['boot_partition']['sha256'],'candidate_logdump_sha256':post['raw']['logdump_partition']['sha256'],
   'boot':boot,'guard':guard,'release':'same-k363-release','version':identity['uname']['version'],'rootfs':'fixture','notes':{}},
  'adopt_result':{'passed':True,'guard_created':True,'old_guards_preserved':True,'old_pointer_backup_preserved':True},
  'receiver':{'passed':True,'transport_exit':0},'endpoint':{'kind':'usb-ipv6','original_key_verified':True,'postboot_Image501_passed':True,
   'host_key_alias':'169.254.42.1','interface_index':29,'peer':m.PEER if hasattr(m,'PEER') else 'fe80::62:bcff:fe28:a101%29','observed_new_boot':boot,'guard_path':guard}}
 def fixture(d):
  for n,value in d.items():(root/(n+'.json')).write_text(json.dumps(value))
  digest=sha((root/'postboot.json').read_bytes())
  for n in ['adoption','adopt_request']:
   value=json.loads((root/(n+'.json')).read_bytes());value['postboot_raw_sha256']=digest;(root/(n+'.json')).write_text(json.dumps(value))
  entries={n:{'path':str(root/(n+'.json')),'sha256':sha((root/(n+'.json')).read_bytes())} for n in d}
  entries['transport']={'path':str(HERE/'transport.py'),'sha256':sha((HERE/'transport.py').read_bytes())}
  key=HERE.parents[1]/'kernel184/host.py';entries['key_transport']={'path':str(key),'sha256':sha(key.read_bytes())}
  pins.write_text(json.dumps(entries))
 docs['postboot']['result']['checks']['instant_gauge'].update(source_type='CDP',source_budget_ua=1500000,hardware_input_ua=900000,SDP_hardware500_observed=False)
 fixture(docs);assert m.reviewed_identity(pins)[:2]==(boot,guard)
 sdp=copy.deepcopy(docs);sdp['postboot']['result']['checks']['instant_gauge'].update(source_type='SDP',source_budget_ua=500000,hardware_input_ua=500000,SDP_hardware500_observed=True)
 fixture(sdp);assert m.reviewed_identity(pins)[:2]==(boot,guard)
 fixture(docs)
 assert m.runtime_expected(pins)['version'].startswith('#501 ')
 for label,edit in [('old boot carrier',lambda d:d['postboot']['raw']['boot_partition'].update(sha256='4126old')),
                    ('old guard',lambda d:d['adopt_request'].update(guard='/var/lib/samurai/old/boot-id-private.txt')),
                    ('flag not accepted',lambda d:d['postboot']['result']['checks']['instant_gauge'].update(flag_Y_and_exact_cmdline=False)),
                    ('wrong endpoint',lambda d:d['endpoint'].update(observed_new_boot='00000000-0000-0000-0000-000000000363'))]:
  bad=copy.deepcopy(docs);edit(bad);fixture(bad)
  try:m.reviewed_identity(pins)
  except ValueError:pass
  else:raise AssertionError(label+' accepted')
groups.append('actual new profile accepts synthetic501 binding and rejects old carrier/guard/flag/endpoint')
result={'schema':'charging-icon-image501-template-tests-v1','passed':True,'runtime_identity_unbound':True,'groups':groups,
 'launcher_sha256':sha((HERE/'launcher.py').read_bytes()),'sha256':m.FROZEN,'manifest_sha256':m.MANIFEST,
 'files':{n:sha((HERE/n).read_bytes()) for n in ['launcher.py','capture-entry.py','transport.py','bind-identity.py','test-template.py']},
 'fixtures_synthetic_no_real_identity_pins':True,'old32_and12_not_rerun':True,'network_device_accessed':False}
(HERE/'template-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert not m.PINS.exists(),'actual identity must not have been manufactured by template tests'
print(json.dumps({'passed':True,'groups':len(groups),'actual_runtime_pins_absent':True,'old_suites_not_rerun':True}))
