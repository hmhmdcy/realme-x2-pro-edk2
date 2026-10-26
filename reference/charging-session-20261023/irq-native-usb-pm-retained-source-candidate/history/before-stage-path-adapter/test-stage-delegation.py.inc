"""New delegation with an actual-stage algorithm and modeled past transport only."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import base64,copy,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
def load(path,name):
 path=Path(str(path).replace('\\','/').replace('E:/','/mnt/e/'))
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=load(HERE/'reviewer.py','retained_stage_delegation_under_test');pins=r.source_check()
prior=json.loads((HERE/'test-result.json').read_bytes())
assert prior['passed'] and prior['methods']==4 and prior['actual_global_pointer_accesses']==0
assert prior['tested_files']['reviewer.py']==r.sha((HERE/'reviewer.py').read_bytes())
runtime_path=Path('/mnt/e/edk2-samurai-out/charging-session-20261023/icon-capture-irq-reattach-runtime/identity-pins-private.json')
saved=json.loads(runtime_path.read_bytes());runtime=saved['reviewed']
update=Path(saved['review_inputs']['update_directory'].replace('E:/','/mnt/e/').replace('\\','/'))
base=json.loads((update.parent/'binding-private.json').read_bytes())['reviewed']
# This return boundary is modeled from the unchanged cache already fully
# reviewed by the four prior tests; it does not re-run that historical suite.
memo=dict(schema='samurai-irq-native-usb-pm-retained-runtime-review-v1',runtime=runtime,base_adoption=base,
 current_pointer_consulted=False,current_device_identity_or_health_verified=False)
h=load(pins['stage_host']['path'],'original_current_stage_request_and_transport_helpers')
hp,values=h.source_check()
d=load(REF/'charging-session-20261023/irq-native-usb-pm-activation-device-candidate/test-delta.py','stage_fixture_definitions_not_suite')
request=h.make_request(d.TX,base,hp['worker']['sha256'],values['payload'])
d.request.clear();d.request.update(request)
with tempfile.TemporaryDirectory() as top:
 root,f,meta,records,processes,claim,raw,response=d.actual_stage_fixture(top)
 binding=dict(schema='samurai-irq-native-usb-pm-stage-binding-v1',transaction_id=d.TX,
  request_sha256=r.sha(raw['request-private.json']),source_pins_sha256=r.sha((h.HERE/'source-pins.json').read_bytes()),
  runtime_pins={'path':str(runtime_path),'sha256':r.sha(runtime_path.read_bytes())},
  source_review_inputs=runtime['review_inputs'],reviewed=runtime,source_adoption=base['adoption'],endpoint=runtime['endpoint'],
  generated_from_actual_runtime_update=True,device_accessed=False)
 (root/'binding-private.json').write_text(json.dumps(binding,indent=2)+'\n')
 (root/'stage-worker.py').write_bytes(values['worker'])
 call=root/'fetch-0123456789abcdef-private';call.mkdir();(call/'raw').mkdir()
 for name,data in raw.items():(call/'raw'/name).write_bytes(data)
 response['files']={name:dict(base64=base64.b64encode(data).decode(),sha256=r.sha(data),bytes=len(data)) for name,data in raw.items()}
 request_raw=raw['request-private.json']
 envelope=dict(action='fetch',request=request,request_sha256=r.sha(request_raw),request_base64=base64.b64encode(request_raw).decode(),
  worker_base64=None,window_confirmed=False,supervisor_base64=None,supervisor_sha256=hp['supervisor']['sha256'])
 (call/'executed-remote.py').write_bytes(('STAGE_TRANSPORT='+repr(envelope)+'\n').encode()+values['remote'])
 key=h.load(hp['key_transport']['path'],'original_key_argv_fixture_only')
 argv=[key.SSH,'-C','-6','-T',*key.OPTIONS,'-o','HostKeyAlias=169.254.42.1','root@fe80::62:bcff:fe28:a101%29','python3 -']
 for name,value in [('transport-child-private.json',dict(pid=999,argv=argv,terminal=False)),
  ('transport-terminal-private.json',dict(pid=999,terminal=True,returncode=0,primary_error=None,cleanup_errors=[])),
  ('stdout-private.json',response),('received-result-private.json',response)]:
  (call/name).write_text(json.dumps(value,indent=2)+'\n')
 wrapped=SimpleNamespace(**vars(h));wrapped.bound=lambda *args,**kwargs:(root,binding,request,request_raw,hp)
 original_load=r.load
 def source_load(path,name):
  if r.local(path)==r.local(pins['stage_host']['path']):return wrapped
  return original_load(path,name)
 with patch.object(r,'load',side_effect=source_load),patch.object(r,'review_retained_runtime',return_value=memo):
  reviewed=r.review_retained_stage(root,call)
  assert reviewed['stage_review']['request']==request and reviewed['stage_review']['source_runtime']==runtime
  assert reviewed['stage_review']['stage']['host_binding_sha256']==r.sha((root/'binding-private.json').read_bytes())
  assert reviewed['current_pointer_consulted'] is False and reviewed['current_device_identity_or_health_verified'] is False
  assert reviewed['stage_review']['actual_device_launch_claim_still_required'] is True
  assert len(reviewed['stage_review']['stage']['evidence'])==17
  (call/'raw/worker-terminal-private.json').write_bytes(b'changed modeled original terminal')
  try:r.review_retained_stage(root,call)
  except ValueError:pass
  else:raise AssertionError('changed original terminal promoted')
report=dict(passed=True,cases=2,actual_stage_algorithm_used_with_device_boundary_models=True,
 historical_transport_and_process_observations_modeled=True,original_fetch_and_chain_and_stage_receipt_functions_executed=True,
 retained_runtime_boundary_reused_from_prior_four_checks=True,
 original_prior_result_sha256=r.sha((HERE/'test-result.json').read_bytes()),
 current_pointer_or_device_modified=False,actual_runtime_request_created=False,
 tested_files={name:r.sha((HERE/name).read_bytes()) for name in ['reviewer.py','source-pins.json','test-stage-delegation.py']})
(HERE/'stage-delegation-test-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':2,'device_accessed':False}))
