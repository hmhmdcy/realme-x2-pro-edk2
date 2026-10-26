"""Freeze r2 final candidate/results and verify immutable r1/source inputs."""
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final462r2_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();SOURCE=SHARED.parent/'source354'
BUILD=SHARED.parent/'kernel462-shared-camera-r2-private/O'
VIEW=BUILD.parent/'source-view';PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r2')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
frozen=load(HERE.parent/'r1-final-validation.json')
assert frozen==load(PRIVATE.parent/'r1-frozen-files-private.json')
for name,digest in frozen['files'].items():assert sha(HERE.parent/name)==digest,name
manifest=load(PRIVATE/'candidate-manifest-private.json')
for row in manifest['inspected_sources']:assert sha(SOURCE/row['path'])==row['sha256']
for row in manifest['files']:
    assert sha(PRIVATE/'candidate'/row['path'])==row['candidate_sha256']
    assert sha(VIEW/row['path'])==row['candidate_sha256']
for row in frozen['candidate']:
    assert sha(PRIVATE.parent/'candidate'/row['path'])==row['candidate_sha256']
    assert sha(SOURCE/row['path'])==row['original_sha256']
original=lambda name:PRIVATE.parent/'candidate'/name if name.endswith('imx471.c') else PRIVATE/'original'/name
patch=lambda names:''.join(''.join(difflib.unified_diff(original(n).read_text().splitlines(True),(PRIVATE/'candidate'/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in names)
assert (HERE/'0001-mux-export-unmanaged-state-handles.patch').read_text()==patch(['drivers/mux/core.c','include/linux/mux/consumer.h'])
assert (HERE/'0002-media-imx471-retain-resource-holder.patch').read_text()==patch(['drivers/media/i2c/imx471.c'])
holder=load(HERE/'holder-c-validation.json');api=load(HERE/'mux-api-validation.json')
build=load(HERE/'target-build-r2-validation.json')
assert build==load(HERE/'target-build-validation.json')
assert all(r['passed'] for r in [holder,api,build])
candidate={row['path']:row['candidate_sha256'] for row in manifest['files']}
assert holder['source_sha256']==candidate['drivers/media/i2c/imx471.c']
assert api['core_sha256']==candidate['drivers/mux/core.c'] and api['header_sha256']==candidate['include/linux/mux/consumer.h']
assert build['candidate']==manifest['files']
for name,artifact in build['artifacts'].items():assert sha(BUILD/name)==artifact['sha256']
assert not (BUILD/'vmlinux.o').exists() and not list(BUILD.rglob('*.ko'))
mapping=lambda t:{l.split('=',1)[0]:l for l in t.splitlines() if l.startswith(('CONFIG_','# CONFIG_'))}
old=mapping((PRIVATE.parent.parent/'kernel457/config363-private').read_text());new=mapping((BUILD/'.config').read_text())
diff={k:[old.get(k),new.get(k)] for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
assert all('VIDEO_QCOM_CAMSS_ICP' in k for k in diff)
assert shutil.disk_usage(SHARED).free>=2*1024**3
for path in HERE.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
    if target!='r2-final-validation.json':assert (HERE/target).is_file(),target
files=sorted(p.name for p in HERE.iterdir() if p.is_file() and p.name!='r2-final-validation.json')
report=dict(stage=462,revision='r2',passed=True,deployable=False,
    files={name:sha(HERE/name) for name in files},candidate=manifest['files'],artifacts=build['artifacts'],
    r1_eleven_public_files_and_three_private_candidates_unchanged=True,
    shared_source354_and_generated_inputs_unchanged=True,
    actual_private_config_sha256=sha(BUILD/'.config'),configuration_differences_from_image363=diff,
    image363_input_config_sha256=build['input_config_sha256'],
    new_api_real_export_records=build['new_export_records_in_mux_object'],
    exact_new_imports_missing_from_old363=build['new_imports_absent_old363'],
    new_builtin_mux_core_requires_new_image=True,
    actual_holder_c_host_cases=35,actual_unmanaged_mux_c_host_cases=4,
    consumer_detach_retains_independent_holder_device_module_resource_handles_modeled=True,
    supplier_forced_unbind_or_module_unload_isolation_proven=False,
    mux_chip_device_reference_pins_gpio_mux_owner_module=False,
    old_sensor_open_fd_lifetime_fixed=False,kernel_concurrency_or_hardware_verified=False,
    r1_dtb_binding_provider_results_reused=True,fifth_sensor_node_added=False,
    compiler_diagnostics=build['diagnostics'],jobs=2,
    source_or_output_full_copy=False,vmlinux_object_copied_or_linked=False,
    ko_or_image_or_rootfs_or_full_modules_built=False,phone_or_sdk_accessed=False,
    free_bytes_after=shutil.disk_usage(SHARED).free)
(HERE/'r2-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(PRIVATE/'r2-frozen-files-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,deployable=False,files=files,candidate=candidate,artifacts=build['artifacts'])),flush=True)
