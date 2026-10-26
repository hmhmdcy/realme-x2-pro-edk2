"""Read final #503 receipts/artifacts only; no build/test/mount or device calls."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OUT=Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')
BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


r=json.loads((HERE/'build-result.json').read_bytes())
assert r['passed'] and r['child_returncode']==0 and r['parent_error'] is None
assert all(r['baseline_trees_preserved'].values())
assert r['parent_mounts_unchanged'] and r['parent_namespace_unchanged']
assert r['shared_sources_unchanged'] and r['shared_critical_inputs_unchanged'] and r['original363_preserved']
assert sha(HERE/'build-result.json')==sha(OUT/'result.json')
run=json.loads((OUT/'execution.json').read_bytes())
assert run['pid']==854 and run['runner_sha256']==sha(HERE/'run-503.py')
ns=json.loads((OUT/'namespace-process.json').read_bytes())
assert ns['terminal'] and ns['returncode']==0
assert r['child_state']['terminal'] and r['child_state']['returncode']==0
proof=json.loads((OUT/'eight-compile-proof.json').read_bytes())
assert len(proof)==8 and set(proof.values())=={1}
assert r['build']['unchanged_other_leaf_count']==3238 and r['build']['unchanged_libstub_count']==32
for n,row in r['build']['outputs'].items():assert sha(OUT/'build'/n)==row['sha256'],n
scope=REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json'
s=json.loads(scope.read_bytes())
assert not s['original778_cached_dwc_importers'] and not s['current481_four_module_cached_dwc_importers']
assert set(proof)==set(s['required_object_targets'])
compat=r['build']['compatibility']
assert compat['builtin_export_count']==15097 and compat['actual_ELF_export_names_exact_502']
assert compat['builtin_export_rows_exact_502'] and compat['Module_symvers_exact_502']
old_refs=[
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json',
 'charging-session-20261023/gauge-image501-repro-candidate/abi-result.json',
 'charging-session-20261023/gauge-image501-abi-provider-supplement/result.json',
 'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json',
 'charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review-result.json',
]
abi=dict(passed=True,scope='consistent private DWC struct users; 502 exports plus frozen cached module receipts',
 actual_503_comparisons=compat,dependency_scope_sha256=sha(scope),
 current_dependency_objects_recompiled=proof,original778_cached_dwc_importers={},current481_cached_dwc_importers={},
 original_modules_or_old_tests_rescanned=False,reused={n:sha(REF/n) for n in old_refs},
 no_new_module_or_runtime_attestation=True,private_internal_dwc_header_changed=True,
 no_universal_type_ABI_claim=True,CONFIG_UTS_RELEASE_unchanged=True,pm_unwind_complete=False)
(HERE/'abi-reuse-result.json').write_text(json.dumps(abi,indent=2)+'\n')
raw_names=['execution.json','namespace-command.json','namespace-process.json','namespace-proof.json',
           'commands.json','phases.json','identity.json','child-state.json','source-delta.json',
           'eight-compile-proof.json','actual-leaf-delta.json','all-object-delta.json',
           'metadata-section-proof.json','compatibility-result.json','B-dwc-eight-objects.log','B-image.log']
execution=dict(passed=True,native_exec_session=74911,parent_pid=854,parent_terminal=True,
               namespace_process=ns,last_make_process=r['child_state'],same_original_exec_waited=True,
               actual_runner_sha256=sha(HERE/'run-503.py'),private_output=str(OUT),
               original_private_502_result_sha256=sha(BASE/'result.json'),
               raw_receipts={n:sha(OUT/n) for n in raw_names},
               no_replay=True,device_access=False,SDK_access=False,Git_used=False)
(HERE/'execution-receipt.json').write_text(json.dumps(execution,indent=2)+'\n')
delivery=dict(schema='samurai-private-dwc-image503-candidate-v1',passed=True,
 files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'},
 outputs=r['build']['outputs'],image_private=str(OUT/'build/arch/arm64/boot/Image'),
 source_changes=r['build']['dwc_sources'],identity=r['identity'],
 eight_actual_object_compiles=proof,unchanged_other_archive_leaves=3238,unchanged_libstub_leaves=32,
 inherited_gauge_and_modules_unchanged=True,pm_unwind_complete=False,
 physical_recovery_proved=False,boot_or_logdump_packaged=False,deployed=False)
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),
                     build_receipt_sha256=sha(HERE/'build-result.json'),abi_receipt_sha256=sha(HERE/'abi-reuse-result.json'),
                     image=r['build']['outputs']['arch/arm64/boot/Image'],
                     vmlinux=r['build']['outputs']['vmlinux'],namespace=ns['pid'])))
