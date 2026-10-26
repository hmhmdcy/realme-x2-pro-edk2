"""Current stage/activation integration only; all device/process boundaries modeled."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,tempfile,unittest
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
c=module('current_pm_device_rules',HERE/'common.py')
o=module('current_pm_operator_rules',HERE/'fastboot-operator.py')
p=module('current_pm_stage_proof',HERE/'stage-proof.py')
m=module('current_pm_materializer',HERE/'materialize.py')
STAGE_TEST=REF/'charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate/test-stage.py'
# Import only the existing fixture definitions. Do not run its eleven old cases.
fixture_source=STAGE_TEST.read_text().split('\ncases=[]',1)[0]
fixture={'__file__':str(STAGE_TEST),'__name__':'stage_fixture_definitions_only'}
exec(compile(fixture_source,str(STAGE_TEST),'exec'),fixture)
u=fixture['u'];Fake=fixture['Fake'];request=fixture['request'];TX=request['transaction_id']
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2)+'\n').encode()

def actual_stage_fixture(top,full=True):
 root=Path(top)/TX;root.mkdir();f=Fake(root,full=full);result=u.stage(request,f,True)
 assert result['staged'],result
 raw={path.name:path.read_bytes() for path in f.out.iterdir() if path.is_file()}
 raw['request-private.json']=f.request_raw
 wargv=['python3','-B',str(c.ROOT/TX/'stage-worker.py'),'--execute-stage']
 sargv=['python3','-B',str(c.ROOT/TX/'stage-supervisor.py'),'--execute-supervisor']
 ident=dict(transaction_id=TX,boot_id=request['identity']['boot_id']);rs=sha(f.request_raw)
 w=dict(ident,pid=111,start_ticks=123,argv=wargv);s=dict(ident,pid=222,start_ticks=456,argv=sargv,request_sha256=rs)
 wl=dict(w,request_sha256=rs,supervisor_pid=222);wt={k:v for k,v in wl.items() if k!='start_ticks'};wt.update(terminal=True,returncode=0)
 st=dict(s,terminal=True,worker_pid=111,worker_returncode=0,returncode=0)
 for name,value in [('process-private.json',w),('worker-launch-receipt-private.json',wl),('worker-terminal-private.json',wt),
  ('launch-receipt-private.json',s),('supervisor-process-private.json',s),('supervisor-terminal-private.json',st)]:raw[name]=encoded(value)
 evidence={};records={}
 for key,path in c.stage_paths(TX).items():
  if key=='worker_source':data=STAGE_TEST.with_name('stage-worker.py').read_bytes()
  elif key=='supervisor_source':data=(REF/'charging-session-20261023/irq-native-usb-pm-stage-host-candidate/supervisor.py').read_bytes()
  else:data=raw[Path(path).name]
  evidence[key]=dict(path=path,sha256=sha(data))
  if key not in ['worker_source','supervisor_source']:records[key]=data if key in ['old_usb','old_manifest'] else json.loads(data)
 fields=dict(transaction_id=TX,request_sha256=rs,result_sha256=sha(raw['result.json']),host_binding_sha256='e'*64,
  worker_sha256=c.STAGE_WORKER,supervisor_sha256=c.STAGE_SUPERVISOR,evidence=evidence)
 meta=dict(c.FIXED,transaction_id='irq-native-usb-pm-activate-offline-fixture',token='d'*48,
  boot_id=request['identity']['boot_id'],soc_serial_sha256=request['identity']['serial_sha256'],
  compatible_sha256=request['identity']['compatible_sha256'],rootfs_release_sha256=request['identity']['rootfs_sha256'],
  adoption=request['adoption'],stage=fields)
 processes={'worker':dict(state='absent',pid=111),'supervisor':dict(state='absent',pid=222)}
 claim=dict(ident,request_sha256=rs,request_count=1,argv=wargv,supervisor_argv=sargv,supervisor_sha256=c.STAGE_SUPERVISOR)
 response=dict(transaction_id=TX,request_sha256=rs,supervisor_receipt=s,launch_receipt=wl,
  supervisor_process=processes['supervisor'],process=processes['worker'],worker_terminal=wt,worker_terminal_verified=True,
  worker_result=result,identity_observation=dict(boot_id=meta['boot_id'],source_boot_same=True,guard_matches=True),
  identity_after=dict(boot_id=meta['boot_id'],source_boot_same=True,guard_matches=True))
 return root,f,meta,records,processes,claim,raw,response

class CurrentIntegration(unittest.TestCase):
 def test_actual_stage_to_guard_full_and_current_tuple(self):
  with tempfile.TemporaryDirectory() as top:
   _,f,meta,records,processes,claim,_,_=actual_stage_fixture(top)
   self.assertEqual(c.validate_stage_records(meta,records,processes,claim),request)
   self.assertEqual(records['before']['sample']['logical_full'],1)
   self.assertEqual(records['after']['sample']['logical_full'],1)
   self.assertEqual(records['after']['sample']['full_holding'],0)
   self.assertEqual(len(meta['stage']['evidence']),17)
   self.assertEqual(set(records['worker_process']),{'transaction_id','boot_id','pid','start_ticks','argv'})
   c.validate_meta_shape(meta,c.ROOT/meta['transaction_id']/'guard-private.json')
   self.assertEqual(c.FIXED['partitions'],['logdump']);self.assertEqual(c.FIXED['unchanged_boot_sha256'],m.OLD_BOOT)
   for edit in [lambda v:v.update(kernel_version=c.FIXED['source_kernel_version']),
                lambda v:v['adoption'].update(postboot_raw_sha256='a'*64),
                lambda v:v.update(transaction_id='usb-irq-protection-activate-offline-fixture')]:
    altered=copy.deepcopy(meta);edit(altered)
    with self.assertRaises((ValueError,KeyError)):c.validate_meta_shape(altered,c.ROOT/meta['transaction_id']/'guard-private.json') if 'postboot_raw_sha256' not in altered['adoption'] else c.validate_stage_records(altered,records,processes,claim)

 def test_failed_partial_old_source_and_unknown_owner_never_promoted(self):
  with tempfile.TemporaryDirectory() as top:
   _,_,meta,records,processes,claim,_,_=actual_stage_fixture(top)
   edits=[lambda r:r['result'].update(staged=False),lambda r:r['result'].update(recovery_error='failed'),
    lambda r:r['result'].update(old_manifest_sha256='5'*64),lambda r:r['result']['temporary_files'].pop(next(iter(r['result']['temporary_files']))),
    lambda r:r['after']['sample'].update(logical_full=0,full_cause=0),
    lambda r:r['worker_terminal'].update(returncode=1),lambda r:r['supervisor_terminal'].update(worker_pid=112),
    lambda r:r['request'].update(schema='samurai-usb-irq-protection-stage-request-v1')]
   for edit in edits:
    changed=copy.deepcopy(records);edit(changed)
    with self.assertRaises((ValueError,KeyError)):c.validate_stage_records(meta,changed,processes,claim)
   for state in ['alive','unknown','pid_reused']:
    changed=copy.deepcopy(processes);changed['worker']['state']=state
    with self.assertRaises(ValueError):c.validate_stage_records(meta,records,changed,claim)
   with self.assertRaises(ValueError):c.validate_stage_records(meta,records,processes,dict(claim,request_count=2))

 def test_stage_host_review_uses_actual_record_shape_without_inventing_claim(self):
  with tempfile.TemporaryDirectory() as top:
   root,_,meta,records,_,_,raw,response=actual_stage_fixture(top)
   call=root/'fetch-0123456789abcdef-private';call.mkdir();(root/'stage-worker.py').write_bytes(STAGE_TEST.with_name('stage-worker.py').read_bytes())
   (root/'binding-private.json').write_bytes(b'fixture binding')
   runtime={'manifest_sha256':c.OLD,'boot_id':meta['boot_id'],'guard_path':request['adoption']['guard_path'],'guard_sha256':request['adoption']['guard_sha256']}
   binding={'reviewed':runtime,'source_review_inputs':{'fixture':'actual boundary replaced'}}
   host=SimpleNamespace(bound=lambda *args,**kw:(root,binding,request,raw['request-private.json'],{}))
   original_load=p.load
   def load(path,name):
    if str(path).endswith('host.py'):return host
    return original_load(path,name)
   with patch.object(p,'load',side_effect=load),patch.object(p,'fetch_raw',return_value=(response,raw)):
    review=p.review_stage(root,call)
    self.assertTrue(review['device_launch_claim_not_exported']);self.assertTrue(review['actual_device_launch_claim_still_required'])
    self.assertEqual(review['stage']['evidence'],meta['stage']['evidence'])
    self.assertNotIn('claim',review);self.assertEqual(p.guard_stage_fields(review),review['stage'])
    response['worker_terminal']['returncode']=1
    with self.assertRaises(ValueError):p.review_stage(root,call)

 def test_fresh_stopped_full_requires_current_source_and_old_live_notes(self):
  with tempfile.TemporaryDirectory() as top:
   _,_,_,records,_,_,_,_=actual_stage_fixture(top)
   data=copy.deepcopy(records['after']);data['charge_behaviour']='auto [inhibit-charge] force-discharge'
   data['limits']['cv_pack_uv']=2*data['limits'].pop('cv_uv')
   self.assertTrue(c.staged_health(data,data['read_end'])['stage_INHIBIT_reverified'])
   for edit in [lambda d:d['source'].update(input_current_limit='100000'),lambda d:d['sample'].update(fault=1),
                lambda d:d['notes'].update({'samurai-usb-input':'08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f'}),
                lambda d:d['sample'].update(full_holding=1)]:
    changed=copy.deepcopy(data);edit(changed)
    with self.assertRaises((ValueError,KeyError)):c.staged_health(changed,changed['read_end'])

 def test_cached_mac_read_holds_same_fd_and_rejects_rebound_instance(self):
  path=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-update/charger-reattach-update-live-001/fetch-b6c23bb0619b2bce-private/raw/after-private.json')
  expected=json.loads(path.read_bytes())['mac_evidence'];raw=base64.b64decode(expected['raw_base64'])
  inode=[expected['attribute_inode']]
  attribute=SimpleNamespace(stat=lambda:SimpleNamespace(st_dev=expected['attribute_dev'],st_ino=inode[0]))
  driver=SimpleNamespace(resolve=lambda:SimpleNamespace(as_posix=lambda:'/sys/bus/platform/drivers/samurai-gauge-protection'))
  class Instance:
   def __truediv__(self,name):return attribute if name=='mac_evidence' else driver
   def stat(self):return SimpleNamespace(st_ino=expected['instance_inode'])
  fakeos=SimpleNamespace(open=lambda *args:99,fstat=lambda fd:SimpleNamespace(st_dev=expected['attribute_dev'],st_ino=expected['attribute_inode']),
   lseek=lambda *args:0,read=lambda *args:raw,O_RDONLY=os.O_RDONLY,O_CLOEXEC=os.O_CLOEXEC,O_NOFOLLOW=os.O_NOFOLLOW,SEEK_SET=os.SEEK_SET)
  c._MAC_FD=None
  try:
   with patch.object(c,'Path',return_value=Instance()),patch.object(c,'os',fakeos):
    c.verify_consumed_cache(expected);self.assertEqual(c._MAC_FD,99);c.verify_consumed_cache(expected)
    inode[0]+=1
    with self.assertRaises(ValueError):c.verify_consumed_cache(expected)
  finally:c._MAC_FD=None

 def test_logdump_only_forward_and_rollback_do_not_reboot(self):
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);a=root/'candidate.img';b=root/'original.img';a.write_bytes(b'A'*64);b.write_bytes(b'B'*64)
   images={'candidate':{'logdump':(a,sha(a.read_bytes()),64)},'original':{'logdump':(b,sha(b.read_bytes()),64)}}
   calls=[]
   def call(label,argv):
    calls.append(argv)
    if label=='devices':return 'SERIAL fastboot\n',''
    if label=='product':return '','product: msmnile\n'
    if label.endswith('-size'):return '',f'partition-size:{label[:-5]}: {96 if label[:-5]=="boot" else 64}\n'
    if label=='flash-logdump':return '',"Writing 'logdump' OKAY\n"
    raise AssertionError((label,argv))
   with patch.object(o,'IMAGES',images),patch.object(o,'SIZES',{'boot':96,'logdump':64}),patch.object(o,'windows_path',side_effect=lambda path:'FAKE:'+str(path)):
    for action in ['flash-candidate','rollback-original']:
     calls.clear();result=o.run_action(action,'SERIAL',call)
     self.assertEqual(result['partitions_written'],['logdump']);self.assertTrue(result['logdump_complete'])
     self.assertEqual(len([x for x in calls if 'flash' in x]),1);self.assertFalse(any('reboot' in x for x in calls))
     self.assertFalse(any('flash' in x and 'boot' in x for x in calls))

 def test_unpassed_carrier_rejected_before_materialization_directory(self):
  proof=m.pinned_fat_proof(False)
  self.assertEqual(proof['unchanged_boot_sha256'],m.OLD_BOOT)
  self.assertEqual(proof['logdumps']['candidate']['sha256'],m.NEW_FAT)
  with tempfile.TemporaryDirectory() as top:
   out=Path(top)/'must-not-exist'
   with patch.object(m,'OUT',out),patch.object(m,'pinned_fat_proof',side_effect=AssertionError('not passed')):
    with self.assertRaises(AssertionError):m.materialize()
   self.assertFalse(out.exists())

 def test_original_hardware_tails_and_unchanged_once_wait_functions_reused(self):
  reuse=json.loads((HERE/'source-reuse.json').read_bytes());op=json.loads((HERE/'operator-source-reuse.json').read_bytes())
  def defs(path):
   source=path.read_text();return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
  old=defs(HERE.parent/'usb-irq-protection-restart-candidate/common.py');new=defs(HERE/'common.py')
  self.assertEqual(len(reuse['exact_common_functions']),17)
  self.assertTrue(all(old[n]==new[n] for n in reuse['exact_common_functions']))
  oldop=defs(REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate/fastboot-operator.py');newop=defs(HERE/'fastboot-operator.py')
  self.assertEqual(len(op['unchanged_operator_functions']),19)
  self.assertTrue(all(oldop[n]==newop[n] for n in op['unchanged_operator_functions']))
  runtime=defs(HERE.parent/'icon-capture-irq-reattach-runtime-candidate/update-review.py');proof=defs(HERE/'stage-proof.py')
  self.assertTrue(all(runtime[n]==proof[n] for n in ['fetch_raw','process_chain']))
  for item in reuse['worker_suffixes']:
   now=(HERE/item['name']).read_text();old=(HERE.parent/'usb-irq-protection-restart-candidate'/item['name']).read_text()
   self.assertEqual(now[now.index('assert len(sys.argv)==4'):].replace("work='irq-native-usb-pm-activation'","work='usb-irq-protection-activation'"),old[old.index('assert len(sys.argv)==4'):])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CurrentIntegration))
 names=['common.py','current-gates.py.inc','eud-quiesce.py','eud-restart.py','fastboot-operator.py','stage-proof.py','stage-proof-body.py.inc',
  'stage-source-pins.json','prepare-contract.json','materialize.py','test-delta.py']
 report=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  tested_files={n:sha((HERE/n).read_bytes()) for n in names},device_accessed=False,old_matrices_rerun=False,
  actual_stage_algorithm_and_atomic_files_used_under_modeled_device=True,actual_runtime_guard_created=False)
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
