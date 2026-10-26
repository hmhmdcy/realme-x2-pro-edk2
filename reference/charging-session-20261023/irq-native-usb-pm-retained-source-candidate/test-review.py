"""Affected retained-source boundaries; never modify the real global pointer."""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import copy,hashlib,importlib.util,json,tempfile,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('retained_current_source_review',HERE/'reviewer.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
RUNTIME=Path('/mnt/e/edk2-samurai-out/charging-session-20261023/icon-capture-irq-reattach-runtime/identity-pins-private.json')
CURRENT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/boot-adoption-private.json')

class RetainedSource(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.denied=[]
  def guard(original):
   def read(path,*args,**kwargs):
    if path.resolve()==CURRENT.resolve():
     cls.denied.append(str(path));raise AssertionError('mutable global pointer must not be consulted')
    return original(path,*args,**kwargs)
   return read
  # All three public Path read entrances reject only the actual mutable pointer.
  # The original adoption/update bytes, code and terminal receipts remain real.
  with patch.object(Path,'read_bytes',guard(Path.read_bytes)),patch.object(Path,'read_text',guard(Path.read_text)),patch.object(Path,'open',guard(Path.open)):
   cls.review=r.review_retained_runtime(RUNTIME)
  cls.pins=r.source_check();cls.host=r.load(cls.pins['stage_host']['path'],'actual_stage_request_helpers_only')

 def test_actual_cached_adoption_and_update_without_global_pointer_access(self):
  self.assertEqual(self.denied,[]);review=self.review
  self.assertFalse(review['current_pointer_consulted']);self.assertFalse(review['current_device_identity_or_health_verified'])
  self.assertEqual(review['runtime']['manifest_sha256'],'18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5')
  self.assertEqual(review['base_adoption']['pointer']['charging_manifest_sha256'],'5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417')
  self.assertNotIn('current_pointer',review['files'])
  self.assertTrue(all(r.local(row['path'])!=CURRENT.resolve() for row in review['files'].values()))
  self.assertTrue(review['runtime']['same_boot_runtime_overlay']);self.assertFalse(review['runtime']['boot_adoption_pointer_rewritten'])

 def test_retained_pointer_can_only_change_location_with_exact_original_bytes(self):
  original=copy.deepcopy(self.review['base_adoption']);replayed=copy.deepcopy(original)
  replayed['files']['current_pointer']=copy.deepcopy(replayed['files']['pointer'])
  value,row=r.reconcile_historical_base(replayed,original,CURRENT)
  self.assertEqual(value,original);self.assertEqual(row,replayed['files']['pointer'])
  for change in [lambda x:x['files']['current_pointer'].update(sha256='0'*64),
                 lambda x:x['files']['current_pointer'].update(path='/different/saved-pointer.json'),
                 lambda x:x.update(boot_id='11111111-2222-4333-8444-555555555555'),
                 lambda x:x['adoption'].update(version='#504 unrelated')]:
   bad=copy.deepcopy(replayed);change(bad)
   with self.assertRaises(ValueError):r.reconcile_historical_base(bad,original,CURRENT)
  bad_original=copy.deepcopy(original);bad_original['files']['current_pointer']['path']='/unrelated/global.json'
  with self.assertRaises(ValueError):r.reconcile_historical_base(replayed,bad_original,CURRENT)

 def test_stage_request_must_derive_from_original_source_identity(self):
  pins,values=self.host.source_check();tx='irq-native-usb-pm-stage-retained-fixture'
  request=self.host.make_request(tx,self.review['base_adoption'],pins['worker']['sha256'],values['payload'])
  binding={'runtime_pins':{'path':str(RUNTIME),'sha256':r.sha(RUNTIME.read_bytes())},
   'reviewed':self.review['runtime'],'source_adoption':self.review['base_adoption']['adoption'],
   'source_review_inputs':self.review['runtime']['review_inputs']}
  with tempfile.TemporaryDirectory() as top:
   out=Path(top);raw=json.dumps(request).encode();captured=[]
   host=SimpleNamespace(bound=lambda *args,**kw:captured.append((args,kw)) or (out,binding,request,raw,pins),
    make_request=self.host.make_request,load=self.host.load)
   with patch.object(r,'review_retained_runtime',return_value=self.review):
    result,source=r.retained_stage_bound(host,tx)
    self.assertEqual(result[2],request);self.assertIs(source,self.review)
    self.assertEqual(captured, [((tx,),{'launching':False})])
    self.assertEqual(list(out.iterdir()),[])
    for change in [lambda q:q['identity'].update(version='#504 wrong source'),
                   lambda q:q['adoption'].update(guard_sha256='0'*64),
                   lambda q:q.update(payload_sha256='0'*64)]:
     bad=copy.deepcopy(request);change(bad)
     host.bound=lambda *args,**kwargs:(out,binding,bad,json.dumps(bad).encode(),pins)
     with self.assertRaises(ValueError):r.retained_stage_bound(host,tx)
    self.assertEqual(list(out.iterdir()),[])

 def test_past_runtime_cannot_replace_missing_actual_stage_originals(self):
  tx='irq-native-usb-pm-stage-retained-missing'
  with tempfile.TemporaryDirectory() as top:
   stage=Path(top)/tx
   with self.assertRaises(FileNotFoundError):r.review_retained_stage(stage,stage/'fetch-0123456789abcdef-private')
   self.assertFalse(stage.exists())

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RetainedSource))
 report=dict(passed=result.wasSuccessful(),methods=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  actual_cached_adoption_and_update_fully_replayed=True,global_pointer_access_traps_installed=True,
  actual_global_pointer_accesses=len(RetainedSource.denied),current_pointer_modified=False,
  stage_binding_boundary_modeled=True,actual_stage_originals_not_available_and_not_fabricated=True,
  current_runtime_identity_or_health_claimed=False,device_accessed=False,old_matrices_rerun=False,
  tested_files={name:r.sha((HERE/name).read_bytes()) for name in ['reviewer.py','source-pins.json','test-review.py']})
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
