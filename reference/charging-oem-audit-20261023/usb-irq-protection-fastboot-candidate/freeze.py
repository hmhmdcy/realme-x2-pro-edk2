"""Freeze only final local sources and run the default inert source check once.
Does not execute tests, create a runtime context, use USB or dispatch fastboot.
"""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
RESTART=REF/'charging-session-20261023/usb-irq-protection-restart-candidate'
STAGE=REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/stage-proof.py'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert not (HERE/'delivery.json').exists(),'already frozen; preserve the original delivery'
files={
 'baseline/operator.py':REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate/fastboot-operator.py',
 'boot/delivery.json':REF/'charging-ui-audit-20261023/usb-input-irq-boot-candidate/delivery.json',
 'boot/result.json':REF/'charging-ui-audit-20261023/usb-input-irq-boot-candidate/result.json',
 'cohort/delivery.json':REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/delivery.json',
 'restart/delivery.json':RESTART/'delivery.json','restart/prepare-contract.json':RESTART/'prepare-contract.json',
 'restart/eud-quiesce.py':RESTART/'eud-quiesce.py','restart/eud-restart.py':RESTART/'eud-restart.py',
 'stage-proof.py':STAGE}
restart=json.loads((RESTART/'delivery.json').read_bytes())
for name in ['prepare-contract.json','eud-quiesce.py','eud-restart.py']:
 expected=restart['files'][name];expected=expected['sha256'] if isinstance(expected,dict) else expected
 assert sha(RESTART/name)==expected,name
assert restart.get('frozen') is True and restart.get('passed') is True
assert (STAGE.parent/'stage-proof-frozen.json').is_file(),'stage-proof final freeze required'
stage_frozen=json.loads((STAGE.parent/'stage-proof-frozen.json').read_bytes())
assert stage_frozen['passed'] is True and stage_frozen['stage_proof_sha256']==sha(STAGE)
pins={'schema':'samurai-usb-irq-protection-fastboot-source-pins-v1','files':{name:sha(path) for name,path in files.items()}}
(HERE/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
test=json.loads((HERE/'test-result.json').read_bytes());assert test['passed'] is True
for name,digest in test['tested_sources'].items():assert sha(HERE/name)==digest,name
assert test['new_changed_boundary_cases']==31 and test['old_suites_rerun'] is False
completion=json.loads((HERE/'completion-test-result.json').read_bytes())
assert completion['passed'] is True and completion['new_cases']==13 and completion['old31_or_old22_rerun'] is False
for name,digest in completion['files'].items():assert sha(HERE/name)==digest,name
for name in ['fastboot-operator.py','completion-proof.py','prepare-source.py','test-operator.py','test-completion.py','freeze.py']:
 ast.parse((HERE/name).read_text())
argv=[sys.executable,'-B',str(HERE/'fastboot-operator.py')]
child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:out,err=child.communicate()
finally:child.wait()
receipt={'pid':child.pid,'argv_kind':'default check-local only','terminal':True,'returncode':child.returncode,
 'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),
 'USB_device_runtime_binding_accessed':False,'test_suite_rerun':False}
if child.returncode!=0:
 (HERE/'local-check-failed.json').write_text(json.dumps({**receipt,'stderr':err.decode(errors='replace')},indent=2)+'\n')
 raise RuntimeError('default source check failed; keep original receipt')
parsed=json.loads(out);assert parsed['passed'] and parsed['usb_accessed'] is False and parsed['files_created'] is False
(HERE/'local-check-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert pins['files']=={name:sha(path) for name,path in files.items()},'frozen dependency changed'
names=['fastboot-operator.py','operator-specialization.inc','prepare-source.py','source-reuse.json',
       'source-pins.json','test-operator.py','test-result.json','completion-proof.py','test-completion.py',
       'completion-test-result.json','local-check-result.json','README.md','freeze.py']
delivery={'schema':'samurai-usb-irq-protection-fastboot-delivery-v1','passed':True,'frozen':True,
 'files':{name:{'sha256':sha(HERE/name),'bytes':(HERE/name).stat().st_size} for name in names},
 'candidate_boot_sha256':'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06',
 'rollback_boot_sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
 'unchanged_logdump_sha256':'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
 'only_write_partition':'boot','new_changed_boundary_cases':31,'new_saved_completion_cases':13,'old_22_cases_rerun':False,
 'unchanged_functions':15,'worker_and_main_only_action_schema_changed':True,
 'default_source_only_returncode':0,'actual_context_guard_or_runtime_request_created':False,
 'device_SSH_USB_fastboot_accessed':False,'rootfs_rollback_proven':False,
 'complete_activation_flow_ready':False,'prepared_Image502_modified':False}
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps({'passed':True,'delivery_sha256':sha(HERE/'delivery.json'),'source_only_child_returncode':child.returncode}))
