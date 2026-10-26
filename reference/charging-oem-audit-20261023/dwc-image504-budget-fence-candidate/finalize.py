"""Bind completed original504 execution/artifacts only; never builds or mounts."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OUT=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01')
BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
def sha(p):
    digest=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):digest.update(data)
    return digest.hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def main():
    assert sys.argv[1:]==['--finalize'] and not sys.flags.optimize
    assert sha(HERE/'plan-delivery.json')=='ea2b5d2bbf6fd2d1be7594ed24a8823456d5d54dcd8e0f8bc86ef40801164ba7'
    plan=json.loads((HERE/'plan-delivery.json').read_bytes())
    for n,row in plan['files'].items():assert sha(HERE/n)==row['sha256'],n
    r=json.loads((HERE/'build-result.json').read_bytes())
    assert sha(HERE/'build-result.json')==sha(OUT/'result.json')
    assert r['passed'] and r['child_returncode']==0 and r['parent_error'] is None
    assert all(r['baseline_trees_preserved'].values()) and len(r['baseline_trees_preserved'])==3
    assert r['parent_mounts_unchanged'] and r['parent_namespace_unchanged']
    assert r['shared_sources_unchanged'] and r['shared_critical_inputs_unchanged'] and r['original363_preserved']
    owner=json.loads((HERE/'owner-result.json').read_bytes())
    assert owner['terminal'] and owner['returncode']==0 and owner['original_exec_session_id']==63242
    run=json.loads((OUT/'execution.json').read_bytes())
    ns=json.loads((OUT/'namespace-process.json').read_bytes())
    assert run['pid']==owner['parent_pid'] and run['runner_sha256']==sha(HERE/'run-504.py')
    assert ns['terminal'] and ns['returncode']==0 and ns['pid']==owner['namespace_pid']
    assert r['child_state']['terminal'] and r['child_state']['returncode']==0
    assert r['child_state']['child_pid']==owner['make_children'][-1]['pid']
    phases=json.loads((OUT/'phases.json').read_bytes())
    assert [p['phase'] for p in phases]==['B-dwc-eight-objects','B-image']
    assert all(p['returncode']==0 for p in phases)
    assert all(p['terminal'] and p['returncode']==0 for p in owner['make_children'])
    proof=json.loads((OUT/'eight-compile-proof.json').read_bytes())
    assert len(proof)==8 and set(proof.values())=={1}
    assert set(proof)==set(r['build']['dwc_dependency_targets'])
    assert r['build']['unchanged_libstub_count']==32
    for n,row in r['build']['outputs'].items():assert sha(OUT/'build'/n)==row['sha256'],n
    assert r['identity']['KBUILD_BUILD_VERSION']=='504'
    assert r['build']['metadata_proof']['old_identity'].startswith('#502 ')
    assert r['build']['metadata_proof']['new_identity'].startswith('#504 ')
    compat=r['build']['compatibility']
    assert compat['builtin_export_count']==15097 and compat['actual_ELF_export_names_exact_502']
    assert compat['builtin_export_rows_exact_502'] and compat['Module_symvers_exact_502']
    assert compat['public_headers_unchanged'] and compat['archive_order_exact']
    assert not compat['diagnostics'] and r['build']['config_exact_original']
    assert r['build']['initramfs_unchanged'] and r['build']['release_unchanged']
    assert r['build']['outputs']['drivers/power/supply/bq27xxx_battery.o']['sha256']=='b30ea227f2326ab6cc73df3407593313f7cbad4d09d5011c9c3df0d56ab6e6d4'
    scope_path=REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json'
    assert sha(scope_path)=='bec66bdf580ce4541f19b60fb5f4865649f48376ba5bbfcc159424455fef8b46'
    scope=json.loads(scope_path.read_bytes())
    assert not scope['original778_cached_dwc_importers'] and not scope['current481_four_module_cached_dwc_importers']
    reused=[
        'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json',
        'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json',
        'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json',
        'charging-session-20261023/gauge-image501-repro-candidate/abi-result.json',
        'charging-session-20261023/gauge-image501-abi-provider-supplement/result.json',
        'charging-oem-audit-20261023/dwc-vbus-budget-fence-candidate/delivery.json',
        'charging-oem-audit-20261023/dwc-vbus-budget-fence-candidate/object-build/delivery.json']
    abi=dict(passed=True,scope='coherent Kbuild DWC header consumers; actual502 exports and frozen cached module evidence',
        actual_504_comparisons=compat,dependency_scope_sha256=sha(scope_path),
        eight_actual_Kbuild_compiles=proof,original778_cached_dwc_importers={},current481_cached_dwc_importers={},
        old_modules_or_functional_tests_rescanned=False,reused={n:sha(REF/n) for n in reused},
        gauge_notify_source_and_object_unchanged=True,default_B_mode_unchanged=True,
        no_universal_type_ABI_or_runtime_claim=True,private_internal_dwc_header_changed=True,
        runtime_on_active_DEVICE_scope=True,auto_direct_complete_supported=False,pm_unwind_complete=False)
    save(HERE/'abi-reuse-result.json',abi)
    names=['execution.json','namespace-command.json','namespace-process.json','namespace-proof.json',
           'commands.json','phases.json','identity.json','child-state.json','source-delta.json',
           'eight-compile-proof.json','actual-leaf-delta.json','all-object-delta.json',
           'metadata-section-proof.json','compatibility-result.json','B-dwc-eight-objects.log','B-image.log']
    execution=dict(passed=True,original_exec_session_id=63242,parent_pid=run['pid'],parent_terminal=True,
        namespace_process=ns,last_make_process=r['child_state'],same_original_exec_waited=True,
        actual_runner_sha256=sha(HERE/'run-504.py'),private_output=str(OUT),
        original_private502_result_sha256=sha(BASE/'result.json'),raw_receipts={n:sha(OUT/n) for n in names},
        no_replay=True,device_SSH_USB_SDK_Git_used=False)
    save(HERE/'execution-receipt.json',execution)
    files=[*plan['files'],'plan-delivery.json','build-result.json','owner-result.json','abi-reuse-result.json',
           'execution-receipt.json','BUILD.md','finalize.py']
    delivery=dict(schema='samurai-private-dwc-image504-budget-fence-candidate-v1',passed=True,
        files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
        frozen_plan_sha256=sha(HERE/'plan-delivery.json'),outputs=r['build']['outputs'],
        image_private=str(OUT/'build/arch/arm64/boot/Image'),source_changes=r['build']['dwc_sources'],identity=r['identity'],
        eight_actual_Kbuild_compiles=proof,unchanged_other_archive_leaves=r['build']['unchanged_other_leaf_count'],
        unchanged_libstub_leaves=32,inherited_gauge_and_modules_unchanged=True,
        runtime_on_active_DEVICE_scope=True,auto_direct_complete_supported=False,
        paired_provider_first_module_sha256='2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448',
        raw_GCC_objects_imported=False,pm_unwind_complete=False,physical_recovery_or_icon_benefit_proved=False,
        modules_dtbs_rootfs_or_carrier_built=False,deployed=False,device_SSH_USB_SDK_Git_used=False,
        archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False))
    save(HERE/'delivery.json',delivery)
    print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),build_result_sha256=sha(HERE/'build-result.json'),
        abi_sha256=sha(HERE/'abi-reuse-result.json'),image=delivery['outputs']['arch/arm64/boot/Image'],vmlinux=delivery['outputs']['vmlinux'])))
if __name__=='__main__':main()
