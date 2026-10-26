"""Freeze named source/test/build receipts. No build, transport or install."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
build=json.loads((HERE/'ko-result.json').read_bytes());tests=json.loads((HERE/'test-result.json').read_bytes());source=json.loads((HERE/'source-result.json').read_bytes())
assert build['passed'] and tests['passed'] and source['passed']
assert build['source_sha256']==source['candidate_source_sha256']==sha((HERE/'samurai-usb-input.c').read_bytes())
assert build['decoder_sha256']==source['decoder_sha256']=='a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'
for name,digest in tests['tested_files'].items():assert sha((HERE/name).read_bytes())==digest,name
assert build['tracked_shared_R7_Image502_inputs_unchanged'] and build['before']==build['after']
assert build['actual_config_values_exact_Image502'] and build['generated_autoconf_exact_Image502']
assert build['imports_all_from_Image502_builtin'] and not build['unresolved_strong_imports'] and not build['diagnostics']
assert len(build['commands'])==2 and all(row['terminal'] is True and row['returncode']==0 for row in build['commands'])
private=Path('E:/edk2-samurai-out/charging-management-20261023/usb-input-flat-consumer-private-01')
assert sha((private/'samurai-usb-input-flat-private.ko').read_bytes())==build['module_sha256']
assert sha((private/'note.gnu.build-id').read_bytes())==build['module_note_sha256']
identity=dict(schema='samurai-usb-input-flat-consumer-module-v1',name='samurai_usb_input',
 target='/lib/modules/'+build['release']+'/extra/samurai-charging/samurai-usb-input.ko',
 private_module_path=str(private/'samurai-usb-input-flat-private.ko'),module_sha256=build['module_sha256'],module_bytes=build['module_bytes'],
 module_note_sha256=build['module_note_sha256'],GNU_build_id=build['GNU_build_id'],
 ELF_machine=build['ELF_machine'],intree=build['intree'],release=build['release'],vermagic=build['vermagic'],
 expected_Image_sha256='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
 actual_config_sha256=build['config_sha256'],actual_Image502_exports_sha256=build['Image502_exports_sha256'],
 strong_import_count=build['strong_import_count'],all_strong_imports_from_Image502_builtin=True,unresolved_strong_imports=[],
 source_sha256=build['source_sha256'],decoder_sha256=build['decoder_sha256'],ko_result_sha256=sha((HERE/'ko-result.json').read_bytes()),
 installed_or_loaded=False,IRQ_or_budget_or_PMIC_or_poll_changed=False,runtime_lifetime_or_type_ABI_verified=False)
(HERE/'module-identity.json').write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8',newline='\n')
files=['prepare.py','samurai-usb-input.c','samurai-usb-input-decode.h','flat-consumer.patch','source-result.json','actual-retain.inc',
 'test-retain.c','run-tests.py','test-result.json','build-ko.py','ko-result.json','module-identity.json','README.md','freeze.py']
delivery=dict(schema='samurai-usb-input-flat-consumer-delivery-v1',passed=True,
 files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in files},
 baseline_source_sha256='b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098',
 decoder_sha256=build['decoder_sha256'],candidate_source_sha256=build['source_sha256'],module_sha256=build['module_sha256'],
 new_actual_function_cases=11,private_ko_W1_Werror_passed=True,old_matrices_rerun=False,
 source_and_shared_inputs_unchanged=True,module_installed_or_loaded=False,device_or_SDK_or_Git_accessed=False,
 archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False,test_binary_or_ko_in_public_leaf=False))
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),module_sha256=build['module_sha256'],identity_sha256=sha((HERE/'module-identity.json').read_bytes()))))
