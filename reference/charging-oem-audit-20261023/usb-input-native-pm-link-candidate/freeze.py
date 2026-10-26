"""Bind explicit source/test/unique-module receipts; no build or deployment."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
build=json.loads((HERE/'ko-result.json').read_bytes())
tests=json.loads((HERE/'test-result.json').read_bytes())
source=json.loads((HERE/'source-result.json').read_bytes())
stage=json.loads((HERE/'source-stage-result.json').read_bytes())
assert build['passed'] and tests['passed'] and source['passed'] and stage['passed']
assert build['source_sha256']==source['source_sha256']==sha(HERE/'samurai-usb-input.c')
assert build['decoder_sha256']==source['decoder_sha256']=='a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'
for name,pin in tests['tested_files'].items():assert sha(HERE/name)==pin,name
for name,row in stage['files'].items():
    actual='source-stage-README.md.inc' if name=='README.md' else name
    assert sha(HERE/actual)==row['sha256'],actual
assert build['before']==build['after'] and build['tracked_shared_R7_Image502_inputs_unchanged']
assert build['actual_config_values_exact_Image502'] and build['generated_autoconf_exact_Image502']
assert build['imports_all_from_Image502_builtin'] and not build['unresolved_strong_imports'] and not build['diagnostics']
assert build['builder_sha256']==sha(HERE/'build-ko.py')
assert len(build['commands'])==2 and all(c['terminal'] is True and c['returncode']==0 for c in build['commands'])
private=Path('E:/edk2-samurai-out/charging-management-20261023/usb-input-native-pm-link-private-01')
module=private/'samurai-usb-input-pm-link-private.ko'
assert sha(module)==build['module_sha256'] and module.stat().st_size==build['module_bytes']
assert sha(private/'note.gnu.build-id')==build['module_note_sha256']
identity=dict(schema='samurai-usb-input-native-pm-link-module-v1',name='samurai_usb_input',
    target='/lib/modules/'+build['release']+'/extra/samurai-charging/samurai-usb-input.ko',
    private_module_path=str(module),module_sha256=build['module_sha256'],module_bytes=build['module_bytes'],
    module_note_sha256=build['module_note_sha256'],GNU_build_id=build['GNU_build_id'],
    ELF_machine=build['ELF_machine'],intree=build['intree'],release=build['release'],vermagic=build['vermagic'],
    expected_Image_sha256='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
    actual_config_sha256=build['config_sha256'],actual_Image502_exports_sha256=build['Image502_exports_sha256'],
    strong_import_count=build['strong_import_count'],all_strong_imports_from_Image502_builtin=True,
    unresolved_strong_imports=[],source_sha256=build['source_sha256'],decoder_sha256=build['decoder_sha256'],
    ko_result_sha256=sha(HERE/'ko-result.json'),installed_or_loaded=False,
    system_PM_ordering_source_verified=True,system_PM_runtime_verified=False,
    budget_or_IRQ_or_PMIC_or_poll_or_old_PM_callbacks_changed=False,runtime_lifetime_or_type_ABI_verified=False)
(HERE/'module-identity.json').write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8',newline='\n')
files=['prepare.py','native-pm-link.c.inc','samurai-usb-input.c','samurai-usb-input-decode.h',
    'native-pm-link.patch','actual-link-and-probe.inc','actual-pm-and-setter.inc','actual-dwc-vbus-work.inc',
    'source-result.json','source-evidence.json','source-stage-result.json','source-stage-README.md.inc',
    'test-native-pm.c','run-tests.py','test-result.json','derive-build.py','build-derivation.json',
    'build-ko.py','ko-result.json','module-identity.json','build-owner-result.json','README.md','freeze.py']
delivery=dict(schema='samurai-usb-input-native-pm-link-delivery-v1',passed=True,
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
    baseline_source_sha256='ee0f0806c5a51576f10b299aca173c61ab2b4764a5954c1039d1c73327878a88',
    decoder_sha256=build['decoder_sha256'],candidate_source_sha256=build['source_sha256'],
    module_sha256=build['module_sha256'],new_actual_function_cases=21,
    original_host_handle=1691,original_host_handle_terminal_returncode=0,
    private_ko_W1_Werror_passed=True,old_matrices_rerun=False,tracked_inputs_unchanged=True,
    module_installed_or_loaded=False,device_or_SDK_or_Git_accessed=False,
    historical_source_stage_README_alias='source-stage-README.md.inc',
    system_PM_runtime_or_r5_or_latency_fix_verified=False,
    archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False,test_binary_or_ko_in_public_leaf=False))
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),
    module_sha256=build['module_sha256'],identity_sha256=sha(HERE/'module-identity.json'),ko_result_sha256=sha(HERE/'ko-result.json'))))
