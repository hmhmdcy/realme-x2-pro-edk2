from pathlib import Path
import ast
import json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
for folder in [ref,out]:
    path=folder/'rollback140-build-validation.json';meta=json.loads(path.read_text())
    meta.update(host_actual_function_cases=12,host_tests_cover_slimbus_unwind139=True,
        eud_unsafe_panic_only_atomic_callback=False,current_phone_kernel_build_before_deploy=143,
        candidate143_eud16_tests_not_rollback_validation=True)
    path.write_text(json.dumps(meta,indent=2)+'\n')
path=ref/'flash-rollback140-logdump.ps1';text=path.read_text()
assert text.count('$build.host_actual_function_cases -ne 16')==1
path.write_text(text.replace('$build.host_actual_function_cases -ne 16','$build.host_actual_function_cases -ne 12'))
text=ref.joinpath('observe-settled-health.py').read_text().replace('k143-settled-health','k143-rollback-settled-health').replace('k143-first-runtime','k143-rollback140-runtime').replace("startswith('#143 ')","startswith('#140 ')").replace('kernel_build=143','kernel_build=140')
assert not ref.joinpath('observe-rollback-health.py').exists();ast.parse(text)
ref.joinpath('observe-rollback-health.py').write_text(text)
print('K143_ROLLBACK_METADATA_REFERS_TO_ACTUAL139_TESTS_AND140_LEGACY_CONSOLE')
