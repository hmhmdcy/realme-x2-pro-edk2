"""Only changed 502 actual functions; transport/USB calls are fake and never spawned."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=module('delta502controller','controller.py');o=module('delta502operator','fastboot-operator.py');m=module('delta502materializer','materialize.py')
def reject(call):
 try:call()
 except (AssertionError,ValueError,KeyError,FileNotFoundError):return
 raise AssertionError('expected rejection')
def fn(source,name):
 node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
 return ''.join(source.splitlines(True)[node.lineno-1:node.end_lineno])
groups=[];cases=0
pins=json.loads((HERE/'baseline-input-pins.json').read_bytes())
raw={n:Path(p['path']).read_bytes() for n,p in pins.items()}
assert all(sha(Path(p['path']))==p['sha256'] for p in pins.values())
profile=c.profile(raw);cases+=1
for name,edit in [('postboot_501',lambda x:(x['raw']['identity_before']['uname'].__setitem__('version','#363 old'),x['raw']['identity_after']['uname'].__setitem__('version','#363 old'))),
                  ('postboot_501',lambda x:x['raw']['logdump_partition'].__setitem__('sha256','aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da')),
                  ('old501_reboot_terminal',lambda x:x.__setitem__('commands_terminal',False)),
                  ('endpoint',lambda x:x.pop('postboot_Image501_passed'))]:
 r=dict(raw);value=json.loads(r[name]);edit(value);r[name]=json.dumps(value).encode();reject(lambda:c.profile(r));cases+=1
groups.append('actual current501 profile and terminal old-transaction provenance; old363/ACA/unknown/old endpoint refused')
guard=(HERE/'guard-fragment.py').read_text();ns={};exec(fn(guard,'charging_sample_phase'),ns);phase=ns['charging_sample_phase']
normal={'logical_full':0,'hold_requested':0,'full_holding':0,'full_cause':0,'desired_enable':1,'session_seconds':100}
full={**normal,'logical_full':1,'hold_requested':1,'full_holding':1,'full_cause':1,'desired_enable':0,'session_seconds':0}
assert phase(normal) and phase(full);cases+=2
assert not phase({**full,'session_seconds':1}) and not phase({**normal,'full_cause':1});cases+=2
stopped={**normal,'desired_enable':0};assert phase(stopped,True) and not phase(stopped);cases+=1
assert phase({**full,'hold_requested':0,'full_holding':0},True);cases+=1
assert not phase({**full,'hold_requested':0,'full_holding':0,'session_seconds':1},True);cases+=1
assert "allow_inhibit=d['action'] in ['inspect-restart','restart']" in (HERE/'remote.py').read_text()
assert "q['terminal'] and q['exit_code']==0 and summary['taint']==0" in guard
groups.append('actual pre-quiesce healthy normal/Full versus bound successful-quiesce INHIBIT phase; no forced charging')
with tempfile.TemporaryDirectory() as td:
 root=Path(td);a=root/'new.img';b=root/'old.img';a.write_bytes(b'A'*64);b.write_bytes(b'B'*64)
 o.IMAGES={'candidate':{'logdump':(a,sha(a),64)},'original':{'logdump':(b,sha(b),64)}};o.SIZES={'boot':96,'logdump':64};o.windows_path=lambda p:'FAKE:'+str(p)
 calls=[]
 def call(label,argv):
  calls.append(argv)
  if label=='devices':return 'SERIAL fastboot\n',''
  if label=='product':return '', 'product: msmnile\n'
  if label.endswith('-size'):
   part=label.removesuffix('-size');return '',f'partition-size:{part}: {o.SIZES[part]}\n'
  if label=='flash-logdump':
   assert argv[-3:-1]==['flash','logdump'];return '',"Writing 'logdump' OKAY\n"
  if label=='reboot':return '',''
  raise AssertionError((label,argv))
 for action,expected in [('flash-candidate',a),('rollback-original',b)]:
  calls.clear();r=o.run_action(action,'SERIAL',call)
  assert r['partitions_written']==['logdump'] and r['logdump_complete']
  writes=[v for v in calls if 'flash' in v];assert len(writes)==1 and writes[0][-1]=='FAKE:'+str(expected)
  assert all(v[-2]!='boot' for v in writes);cases+=1
 assert o.run_action('reboot-candidate','SERIAL',call)['boot_success_proven'] is False;cases+=1
 action=root/'flash-candidate';action.mkdir();(action/'request-private.json').write_text('{}')
 good={'claimed_ns':1,'action':'flash-candidate','passed':True,'terminal':True,'commands_terminal':True,
       'partitions_written':['logdump'],'logdump_complete':True,'flashed_images_sha256':o.image_hashes('candidate')}
 (action/'result-private.json').write_text(json.dumps(good));assert o.reboot_binding(root,'reboot-candidate')['images_sha256']==o.image_hashes('candidate');cases+=1
 (action/'result-private.json').write_text(json.dumps({**good,'partitions_written':['logdump','boot']}));reject(lambda:o.reboot_binding(root,'reboot-candidate'));cases+=1
 (action/'result-private.json').unlink();reject(lambda:o.prior_terminal(root,'rollback-original'));cases+=1
 (action/'result-private.json').write_text(json.dumps({**good,'commands_terminal':False}));reject(lambda:o.prior_terminal(root,'rollback-original'));cases+=1
groups.append('actual logdump-only flash/7e5 rollback/reboot evidence; boot never written; incomplete/unknown cannot advance')
with tempfile.TemporaryDirectory() as td:
 root=Path(td);old_activation=o.ACTIVATION;o.ACTIVATION=root
 for name in ['prepare-contract.json','eud-restart.py']:(root/name).write_text('exact '+name)
 bound={n:sha(root/n) for n in ['prepare-contract.json','eud-restart.py']}
 (root/'activation-pins.json').write_text(json.dumps(bound));assert o.pinned_tools()==bound;cases+=1
 (root/'eud-restart.py').write_text('changed');reject(o.pinned_tools);cases+=1
 o.ACTIVATION=old_activation
with tempfile.TemporaryDirectory() as td:
 old_load,old_checked,old_out=m.load,m.checked,m.OUT
 m.OUT=Path(td)/'not-created';m.checked=lambda *args:Path('/FAKE')
 def fake_load(p):
  if Path(p).name=='fat-input-pin.json':return {'ready':True,'delivery_sha256':'a'*64,'logdump_result_sha256':'b'*64}
  return {'passed':False}
 m.load=fake_load
 reject(m.materialize);assert not m.OUT.exists();cases+=1
 m.load,m.checked,m.OUT=old_load,old_checked,old_out
groups.append('actual materialize rejects missing/unpassed FAT before creating a prepare contract/directory')
oldc=(REF/'charging-session-20261023/gauge-image501-activation-candidate/controller.py').read_text()
oldp=(REF/'charging-session-20261023/gauge-image501-fastboot-pair-candidate/fastboot-operator.py').read_text()
unchanged={}
for file,old,names in [('controller.py',oldc,['create','save','load_json','fact','process_identity','process_status','ssh_worker','start_job','terminal_job','require_known','reconcile','fetch_reconcile','retain_fetch','copy_exact','host_jobs']),
 ('fastboot-operator.py',oldp,['require','sha','read_json','fsync_dir','once','publish_result','locked','reference_file','process_info','command','windows_path','prior_terminal','claim_action'])]:
 now=(HERE/file).read_text()
 for n in names:
  assert fn(now,n)==fn(old,n),(file,n)
  unchanged[file+'::'+n]=hashlib.sha256(fn(now,n).encode()).hexdigest()
groups.append('28 unchanged actual control/join/once-intent functions bound to old receipts; old suites not rerun')
result={'passed':True,'affected_groups':len(groups),'cases':cases,'groups':groups,
 'tested_files':{n:sha(HERE/n) for n in ['controller.py','remote.py','guard-fragment.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py','materialize.py','test-delta.py']},
 'unchanged_functions':unchanged,'old_suites_reused_not_rerun':True,
 'old_receipts':{str(p.relative_to(REF)):sha(p) for p in [REF/'charging-session-20261023/gauge-image501-activation-candidate/test-result.json',REF/'charging-session-20261023/gauge-image501-fastboot-pair-candidate/test-result.json',REF/'charging-session-20261023/gauge-image501-fastboot-pair-candidate/context-test-result.json']},
 'boundaries':'actual changed functions; transport/USB mocked; source/receipts local only',
 'device_SSH_USB_fastboot_or_build_executed':False,'valid_prepare_contract_generated_by_tests':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'affected_groups':len(groups),'cases':cases,'test_receipt_sha256':sha(HERE/'test-result.json')}))
