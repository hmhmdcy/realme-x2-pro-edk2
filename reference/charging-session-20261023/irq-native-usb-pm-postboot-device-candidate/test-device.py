"""Two current postboot profiles on explicit models derived from preserved old raw."""
from pathlib import Path
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load(HERE/'device.py','actual_current_pm_postboot_device');ip=load(HERE/'identity-probe.py','actual_current_pm_postboot_identity')
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
CACHED=BASE/'usb-irq-protection-activation/usb-irq-protection-activate-live-001/postboot-r1-01-private'
old_report=(CACHED/'stdout-private.json').read_bytes();old_request=(CACHED/'request-private.json').read_bytes()
inventory=BASE/'native-usb-pm-current-readonly-01-private/stdout-private.json'
before_hashes={str(path):m.sha(path.read_bytes()) for path in [CACHED/'stdout-private.json',CACHED/'request-private.json',inventory]}
def cache():
 raw=b'schema=1 attempted=0 terminal=0\n'
 return dict(sha256=m.sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=1,attribute_inode=101,instance_inode=102)
def fixture(profile):
 observed=json.loads(old_report);assert observed['result']['passed'] is True and len(observed['result']['checks'])==10
 raw=copy.deepcopy(observed['raw']);row=m.PROFILES[profile]
 oldboot='11111111-1111-4111-8111-111111111111';newboot='22222222-2222-4222-8222-222222222222'
 for side in ['identity_before','identity_after']:raw[side]['boot_id']=newboot;raw[side]['uname']['version']=row['version']
 raw['boot_partition']['sha256']=m.IRQ_BOOT;raw['logdump_partition']['sha256']=row['logdump']
 raw['manifest']['sha256']=row['manifest_sha256'];raw['manifest_text']=json.dumps(row['manifest'])
 for target,digest in row['manifest']['installed_files'].items():raw['installed_files'][target]['sha256']=digest
 for name,info in row['manifest']['modules'].items():
  note=row['notes'][name.replace('-','_')]
  raw['charging_modules'][name].update(sha256=info['sha256'],disk_note_sha256=note,loaded_note_sha256=note,loaded_note_matches_disk=True)
 raw['protection_cache_before']=cache();raw['protection_cache_after']=cache()
 pm=json.loads(inventory.read_bytes());raw['native_pm']={key:pm[key] for key in ['controller','provider']}
 if row['system_pm_link']:
  ctrl,provider=raw['native_pm']['controller'],raw['native_pm']['provider']
  link=dict(target='/sys/devices/virtual/devlink/modeled-dwc-to-current-input',consumer=ctrl['path'],supplier=provider['path'],runtime_pm='0',sync_state_only='0',status='not tracked')
  ctrl['links'].append(dict(link,name='supplier:platform:modeled-input'));provider['links'].append(dict(link,name='consumer:platform:a600000.usb'))
 identity=raw['identity_before'];forward=profile=='forward_504'
 tx=('irq-native-usb-pm-stage-' if forward else 'irq-native-usb-pm-rollback-')+'postboot-fixture'
 activation=('irq-native-usb-pm-activate-' if forward else 'irq-native-usb-pm-rollback-activate-')+'postboot-fixture'
 stage=dict(schema='samurai-irq-native-usb-pm-stage-result-v1' if forward else 'samurai-irq-native-usb-pm-cold-rollback-result-v1',
  transaction_id=tx,terminal=True,runtime_pending=True,stop_verified=True,primary_error=None,
  status='staged/runtime_pending' if forward else 'staged_original/runtime_pending',disk_state='all_new_fsynced' if forward else 'all_original_fsynced')
 if forward:stage.update(staged=True,old_manifest_sha256=m.PROFILES['restored_502']['manifest_sha256'],new_manifest_sha256=row['manifest_sha256'])
 else:stage.update(restored=True,unknown_write_state=False)
 source=m.PROFILES['restored_502' if forward else 'forward_504']['version']
 guard=dict(transaction_id=tx,boot_id=oldboot,new_boot_id=newboot,kernel_release=identity['uname']['release'],source_kernel_version=source,
  target_kernel_version=row['version'],rootfs_release_sha256=identity['rootfs']['sha256'],soc_serial_sha256=identity['serial_sha256'],
  compatible_sha256=m.sha(base64.b64decode(identity['compatible_b64'])),candidate_boot_sha256=m.IRQ_BOOT,
  candidate_logdump_sha256=row['logdump'],image_sha256=row['image'],partitions=['logdump'])
 request=dict(schema='samurai-irq-native-usb-pm-postboot-readonly-v1',profile=profile,new_endpoint='fe80::62:bcff:fe28:a101%29',
  original_key_transport_verified=True,context_sha256='a'*64,guard_sha256='b'*64,stage_result_sha256='c'*64,guard=guard,stage=stage,
  camera=json.loads(old_request)['camera'],activation_transaction_id=activation,
  activation_guard=dict(transaction_id=activation,boot_id=oldboot,kernel_version=row['version'] if forward else source,source_kernel_version=source),new_boot_id=newboot)
 return raw,request

class CurrentPostboot(unittest.TestCase):
 def test_original_functions_collector_body_and_cache_methods_reused(self):
  pins=json.loads((HERE/'source-pins.json').read_bytes())
  for name,row in pins.items():
   path=Path(str(row['path']).replace('\\','/'))
   if len(str(path))>2 and str(path)[1:3]==':/':path=Path('/mnt/'+str(path)[0].lower()+str(path)[2:])
   raw=path.read_bytes();self.assertEqual(m.sha(raw),row['sha256']);self.assertEqual(len(raw),row['bytes'])
  def funcs(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
  def method(text,cls,name):
   node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==cls)
   return ast.get_source_segment(text,next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name))
  old=(HERE.parents[1]/'charging-oem-audit-20261023/irq-cohort-postboot-readonly/device.py').read_text();new=(HERE/'device.py').read_text()
  reuse=json.loads((HERE/'source-reuse.json').read_bytes());self.assertEqual(len(reuse['unchanged_original_functions']),25)
  for name in reuse['unchanged_original_functions']:self.assertEqual(funcs(old)[name],funcs(new)[name])
  self.assertEqual(funcs(old)['collect'].replace('def collect(','def collect_base(',1),funcs(new)['collect_base'])
  probe=(HERE.parent/'irq-native-usb-pm-rollback-host-candidate/current-probe.py').read_text()
  for old_cls,new_cls,name in [('ProbeIdentity','CacheEvidence','cache_evidence'),('Probe','CacheFile','open_cache'),('Probe','CacheFile','close')]:
   self.assertEqual(method(probe,old_cls,name),method(new,new_cls,name))

 def test_both_profiles_complete_twelve_gate_audit_and_wrong_combinations(self):
  for profile in m.PROFILES:
   raw,request=fixture(profile);result=m.audit(raw,request)
   self.assertTrue(result['passed'],result);self.assertEqual(len(result['checks']),12)
   self.assertEqual(result['hardware_writes'],0);self.assertFalse(result['guard_created'])
   for change,gate in [(lambda r:r['identity_after']['uname'].update(version='wrong'),'identity_after'),
    (lambda r:r['logdump_partition'].update(sha256='0'*64),'partitions'),
    (lambda r:r['manifest'].update(sha256='0'*64),'cohort_install'),
    (lambda r:r['charging_modules']['samurai-usb-input'].update(loaded_note_sha256='0'*64),'cohort_install')]:
    bad=copy.deepcopy(raw);change(bad);result=m.audit(bad,request)
    self.assertFalse(result['passed']);self.assertIn(gate,result['errors'])

 def test_stateless_pair_direction_flags_and_current_premise(self):
  raw,request=fixture('forward_504');m.validate_request(request)
  self.assertFalse(m.check_pm_topology(raw,request)['system_suspend_or_resume_or_USB_recovery_accepted'])
  mutations=[lambda r:r['native_pm']['controller']['links'].pop(),lambda r:r['native_pm']['provider']['links'].pop(),
   lambda r:r['native_pm']['controller']['links'][-1].update(runtime_pm='1'),
   lambda r:r['native_pm']['provider']['links'][-1].update(status='active'),
   lambda r:r['native_pm']['controller']['power'].update(control='auto'),
   lambda r:r['native_pm']['provider'].update(path='/sys/devices/platform/other')]
  for change in mutations:
   bad=copy.deepcopy(raw);change(bad)
   with self.assertRaises(AssertionError):m.check_pm_topology(bad,request)
  raw,request=fixture('restored_502');self.assertFalse(m.check_pm_topology(raw,request)['stateless_dependency_observed'])

 def test_cache_full_unknown_budget_and_source_result_rejections(self):
  raw,request=fixture('forward_504');full=copy.deepcopy(raw)
  for field in ['telemetry_before','telemetry_after']:
   sample=m.parse_kv(full[field]);sample.update(logical_full=1,hold_requested=1,full_holding=1,full_cause=3,desired_enable=0,session_seconds=0)
   full[field]=' '.join(str(key)+'='+str(value) for key,value in sample.items())
  self.assertTrue(m.audit(full,request)['passed'])
  bad=copy.deepcopy(raw);bad['source']['current_max']={'errno':61}
  self.assertFalse(m.audit(bad,request)['passed'])
  for change in [lambda r:r['protection_cache_after'].update(instance_inode=999),
   lambda r:r['protection_cache_before'].update(sha256='0'*64)]:
   bad=copy.deepcopy(raw);change(bad)
   self.assertFalse(m.audit(bad,request)['passed'])
  for profile in m.PROFILES:
   raw,req=fixture(profile)
   for change in [lambda q:q['guard'].update(candidate_boot_sha256='0'*64),lambda q:q['stage'].update(stop_verified=False),
    lambda q:q['guard'].update(new_boot_id=q['guard']['boot_id']),lambda q:q['stage'].update(primary_error={'unknown':True})]:
    bad=copy.deepcopy(req);change(bad)
    with self.assertRaises(AssertionError):m.validate_request(bad)

 def test_identity_probe_target_versions_and_new_boot(self):
  for profile in m.PROFILES:
   raw,request=fixture(profile);ip.EXPECTED_VERSION=m.PROFILES[profile]['version']
   self.assertTrue(ip.check_identity(raw['identity_before'],request['guard'])['new_boot'])
   bad=copy.deepcopy(raw['identity_before']);bad['boot_id']=request['guard']['boot_id']
   with self.assertRaises(AssertionError):ip.check_identity(bad,request['guard'])
   bad=copy.deepcopy(raw['identity_before']);bad['uname']['version']=m.PROFILES['restored_502' if profile=='forward_504' else 'forward_504']['version']
   with self.assertRaises(AssertionError):ip.check_identity(bad,request['guard'])

 def test_real_readonly_cache_fd_and_collection_failure_cleanup(self):
  with tempfile.TemporaryDirectory() as top:
   instance=Path(top)/'instance';instance.mkdir();(instance/'driver').symlink_to('/sys/bus/platform/drivers/samurai-gauge-protection')
   raw=b'schema=1 attempted=0 terminal=0\n';(instance/'mac_evidence').write_bytes(raw)
   with patch.object(m,'INSTANCE',str(instance)):
    reader=m.CacheReader()
    try:
     reader.open_cache();before=reader.cache_evidence();self.assertEqual(before['raw_base64'],base64.b64encode(raw).decode())
     replacement=instance/'replacement';replacement.write_bytes(raw);replacement.replace(instance/'mac_evidence')
     with self.assertRaises(RuntimeError):reader.cache_evidence()
    finally:reader.close()
    self.assertIsNone(reader.mac_fd)
  raw,request=fixture('forward_504');events=[]
  class Reader:
   def __init__(self):events.append('create')
   def open_cache(self):events.append('open');raise OSError('modeled cache open failure')
   def close(self):events.append('close')
  with patch.object(m,'identity',return_value=raw['identity_before']),patch.object(m,'CacheReader',Reader):
   with self.assertRaises(OSError):m.collect(request)
  self.assertEqual(events,['create','open','close']);events.clear()
  wrong=copy.deepcopy(raw['identity_before']);wrong['uname']['version']='wrong'
  with patch.object(m,'identity',return_value=wrong),patch.object(m,'CacheReader',Reader):
   with self.assertRaises(AssertionError):m.collect(request)
  self.assertEqual(events,[])

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(CurrentPostboot);result=unittest.TextTestRunner(verbosity=2).run(suite)
 assert all(m.sha(Path(path).read_bytes())==digest for path,digest in before_hashes.items())
 report=dict(passed=result.wasSuccessful(),groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),profiles=list(m.PROFILES),
  both_profile_models_gate_count=12,old_cached_bytes_unchanged=True,modeled_current_facts_not_new_hardware_evidence=True,
  real_temp_readonly_cache_fd_used=True,device_accessed=False,actual_runtime_request_created=False,old_matrices_rerun=False,
  cached_source_hashes=before_hashes,files={name:m.sha((HERE/name).read_bytes()) for name in ['device.py','identity-probe.py','profiles.json','prepare.py','current-body.py.inc','test-device.py']})
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
