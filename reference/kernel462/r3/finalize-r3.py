"""Freeze r3 without changing r1/r2, shared sources or generated inputs."""
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();SOURCE=SHARED.parent/'source354'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3')
BUILD=SHARED.parent/'kernel462-shared-camera-r3-private/O'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
for part in ['r1','r2']:
    directory=HERE.parent if part=='r1' else HERE.parent/'r2'
    record=load(directory/(part+'-final-validation.json'))
    assert record==load(PRIVATE.parent/('' if part=='r1' else part)/(part+'-frozen-files-private.json'))
    for name,digest in record['files'].items():assert sha(directory/name)==digest
    for row in record['candidate']:
        directory_private=PRIVATE.parent if part=='r1' else PRIVATE.parent/'r2'
        assert sha(directory_private/'candidate'/row['path'])==row['candidate_sha256']
manifest=load(PRIVATE/'candidate-manifest-private.json')
candidate=PRIVATE/'candidate/drivers/media/i2c/imx471.c';old=PRIVATE.parent/'r2/candidate/drivers/media/i2c/imx471.c'
assert sha(candidate)==manifest['candidate_sha256'] and sha(old)==manifest['r2_imx471_sha256']
patch=''.join(difflib.unified_diff(old.read_text().splitlines(True),candidate.read_text().splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
assert patch==(HERE/'0001-media-imx471-retain-sensor-until-final-release.patch').read_text()
inspection=load(PRIVATE/'source-lifetime-inspection-private.json')
for row in inspection['files']:
    assert sha(SOURCE/row['path'])==row['source_sha256']
    assert sha(PRIVATE/'source'/row['path'])==row['source_sha256']
chain=load(HERE/'source-chain-validation.json');tests=load(HERE/'lifetime-c-validation.json')
build=load(HERE/'object-build-r2-validation.json')
assert build==load(HERE/'object-build-validation.json')
assert chain['passed'] and tests['passed'] and build['passed']
assert tests['source_sha256']==build['candidate_sha256']==sha(candidate)
assert tests['r2_late_close_uaf_negative_witness'] and tests['old_core_post_release_uaf_negative_witness']
assert sha(BUILD/'drivers/media/i2c/imx471.o')==build['object']['sha256']
assert sha(BUILD.parent/'source-view/drivers/media/i2c/imx471.c')==sha(candidate)
assert not (BUILD/'vmlinux.o').exists() and not list(BUILD.rglob('*.ko'))
headers=['include/linux/atomic.h','include/linux/kref.h','include/linux/slab.h','include/linux/list.h',
         'include/linux/mutex.h','include/linux/pm_runtime.h','include/media/v4l2-subdev.h',
         'include/media/v4l2-ctrls.h','include/media/v4l2-device.h']
matched={}
for name in headers:
    raw=(SOURCE/name).read_bytes()
    assert raw==subprocess.check_output(['git','-C',str(SOURCE),'show',inspection['commit']+':'+name])
    matched[name]=sha(SOURCE/name)
mapping=lambda s:{l.split('=',1)[0]:l for l in s.splitlines() if l.startswith(('CONFIG_','# CONFIG_'))}
a=mapping((PRIVATE.parent.parent/'kernel457/config363-private').read_text());b=mapping((BUILD/'.config').read_text())
diff={k:[a.get(k),b.get(k)] for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
assert all('VIDEO_QCOM_CAMSS_ICP' in k for k in diff)
assert shutil.disk_usage(SHARED).free>=2*1024**3
for path in HERE.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
    if target!='r3-final-validation.json':assert (HERE/target).is_file(),target
files=sorted(p.name for p in HERE.iterdir() if p.is_file() and p.name!='r3-final-validation.json')
report=dict(stage=462,revision='r3',passed=True,deployable=False,files={name:sha(HERE/name) for name in files},
    candidate_sha256=sha(candidate),r2_base_sha256=sha(old),object=build['object'],
    reachable_original363_chain_functions=len(chain['functions']),all_chain_functions_equal_image363=True,
    actual_c_host_cases=18,r2_late_close_uaf_negative_witness=True,old_core_release_uaf_negative_witness=True,
    r2_holder_section_sha256=manifest['r2_holder_section_sha256'],r2_actual_holder_proof_reused_without_rerun=True,
    driver_base_and_framework_refs_and_delayed_cleanup_modeled=True,
    new_open_close_sensor_pm_reference_added=False,all_old_fd_sensor_instances_freed_in_model=True,
    real_kernel_concurrent_open_ioctl_stream_graph_unbind_verified=False,
    controlled_unbind_requires_no_new_open_or_stream_requests=True,
    provider_forced_unbind_or_module_unload_fixed=False,
    requires_combined_core0064_and_r2_mux_exports=True,k456_image_alone_lacks_r2_exports=True,
    public_api_headers_equal_original363=matched,configuration_differences_from_image363=diff,
    source354_shared_generated_and_frozen_r1_r2_unchanged=True,
    compiler_diagnostics=build['diagnostics'],jobs=2,free_bytes=shutil.disk_usage(SHARED).free,
    ko_or_image_or_rootfs_or_full_modules_built=False,whole_source_or_O_or_vmlinux_object_copied=False,
    sdk_or_phone_accessed=False,fifth_node_dt_or_optical_parameters_changed=False)
(HERE/'r3-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(PRIVATE/'r3-frozen-files-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,deployable=False,files=files,candidate_sha256=sha(candidate),object=build['object'])),flush=True)
