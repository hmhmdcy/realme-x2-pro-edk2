"""Freeze proven r1 inputs/results without rebuilding anything."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final462_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mount.mounted_build();source=shared.parent/'source354'
private=Path('/mnt/e/edk2-samurai-out/kernel462');build=shared.parent/'kernel462-shared-camera-private/O'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
assert shutil.disk_usage(shared).free>=2*1024**3
original=load(HERE.parent/'kernel363/boot-candidate-build-validation.json')['commit']
provider_sources={}
for name in ['drivers/mux/core.c','drivers/mux/gpio.c','drivers/mux/Makefile','drivers/reset/core.c','drivers/reset/reset-gpio.c']:
    raw=(source/name).read_bytes()
    assert raw==subprocess.check_output(['git','-C',str(source),'show',original+':'+name])
    provider_sources[name]=sha(source/name)
manifest=load(private/'candidate-manifest-private.json')
assert all(sha(private/'candidate'/row['path'])==row['candidate_sha256'] and sha(source/row['path'])==row['original_sha256'] for row in manifest['files'])
mapping=lambda text:{line.split('=',1)[0]:line for line in text.splitlines() if line.startswith(('CONFIG_','# CONFIG_'))}
old=mapping((private.parent/'kernel457/config363-private').read_text());new=mapping((build/'.config').read_text())
diff={key:[old.get(key),new.get(key)] for key in sorted(old.keys()|new.keys()) if old.get(key)!=new.get(key)}
assert all('VIDEO_QCOM_CAMSS' in key for key in diff),diff
for name in ['target-build-r1-validation.json','resource-c-validation.json','binding-provider-validation.json']:assert load(HERE/name)['passed']
files=['README.md','0001-media-imx471-use-shared-route-and-reset.patch','prepare-resources.py','build-targets.py',
       'check-resource-c.py','check-binding-providers.py','target-build-r1-validation.json','resource-c-validation.json',
       'binding-provider-validation.json','finalize-r1.py']
result=dict(stage=462,revision='r1',passed=True,deployable=False,files={name:sha(HERE/name) for name in files},
    candidate=manifest['files'],provider_sources_equal_original363=provider_sources,
    input_config_exact_image363=True,actual_private_config_sha256=sha(build/'.config'),
    actual_private_config_differences=diff,source354_inputs_unchanged=True,
    object_and_dtb_built=True,ko_or_image_or_rootfs_or_full_modules_built=False,
    c_compiler_zero_diagnostics=True,dtc_existing_location_warnings=2,
    runtime_reference_fault_cases=16,probe_remove_active_devres_quarantine_completed=False,
    historical_matching_provider_modules_reused=True,current_phone_provider_ready_not_verified=True,
    fifth_node_or_dynamic_phy_inputs_added=False,phone_or_sdk_accessed=False,free_bytes=shutil.disk_usage(shared).free)
(HERE/'r1-final-validation.json').write_text(json.dumps(result,indent=2)+'\n')
(private/'r1-frozen-files-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,deployable=False,files=len(files),config_differences=diff)),flush=True)
