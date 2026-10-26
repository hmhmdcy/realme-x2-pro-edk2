"""Validate the already linked r2 module after correcting an export-count check."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel468')
spec=importlib.util.spec_from_file_location('inspect468_storage',HERE.parent/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);shared=storage.mount.mounted_build()
source=shared.parent/'source354';isolated=shared.parent/'kernel468-tele-mode2-private';build=isolated/'O'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((PRIVATE/'candidate-manifest-private.json').read_bytes())
original=json.loads((HERE.parent/'kernel363/boot-candidate-build-validation.json').read_bytes())
snapshot=json.loads((PRIVATE/'source-inspection-private.json').read_bytes())
for row in snapshot['files']:
    if 'file' in row:assert sha(source/row['file'])==row['sha256']
    elif 'build' in row:assert sha(shared/row['build'])==row['sha256']
for name,key in [('s5k3m5.c','candidate_sha256'),('s5k3m5-19mhz-tables.h','header_sha256')]:
    assert sha(isolated/'source-view/drivers/media/i2c'/name)==sha(PRIVATE/'candidate/drivers/media/i2c'/name)==manifest[key]
log=PRIVATE/'module-build-r2-private.log';text=log.read_text()
diagnostics=[line for line in text.splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
assert not diagnostics
for target in ['drivers/media/i2c/s5k3m5.ko','drivers/media/v4l2-core/v4l2-cci.ko']:assert 'LD [M]  '+target in text
ko=PRIVATE/'s5k3m5-mode2-build2.ko';assert sha(ko)==sha(build/'drivers/media/i2c/s5k3m5.ko')
info=lambda field:subprocess.check_output(['modinfo','-F',field,str(ko)],text=True).strip()
assert info('intree')=='Y' and info('vermagic').split()[0]==original['release'] and info('depends')=='v4l2-cci'
old={row.split()[1]:row.split() for row in (shared/'Module.symvers').read_text().splitlines()}
assert sha(shared/'Module.symvers')==original['artifacts']['Module.symvers']['sha256']
exports=[row.split() for row in (build/'Module.symvers').read_text().splitlines() if row.split()[2].endswith('/v4l2-cci')]
assert len(exports)==5 and all(row==old[row[1]] for row in exports)
imports={row.split()[-1] for row in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(ko)],text=True).splitlines() if row.strip()}
assert imports<=old.keys()
config=(PRIVATE.parent/'kernel457/config363-private').read_bytes();assert hashlib.sha256(config).hexdigest()==original['artifacts']['.config']['sha256']
cfg=lambda raw:{l.split('=',1)[0]:l for l in raw.decode().splitlines() if l.startswith(('CONFIG_','# CONFIG_'))}
a=cfg(config);b=cfg((build/'.config').read_bytes());diff={k:[a.get(k),b.get(k)] for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
assert all('VIDEO_QCOM_CAMSS_ICP' in key for key in diff)
headers=['include/media/v4l2-subdev.h','include/media/v4l2-ctrls.h','include/media/v4l2-cci.h','include/linux/pm_runtime.h','include/linux/regulator/consumer.h','include/linux/i2c.h']
assert all(subprocess.check_output(['git','-C',str(source),'show',original['commit']+':'+p])==(source/p).read_bytes() for p in headers)
assert not (build/'vmlinux.o').is_symlink() and sha(build/'vmlinux.o')==sha(shared/'vmlinux.o')
assert shutil.disk_usage(shared).free>=2*1024**3
report=dict(stage=468,attempt=2,passed=True,raw_build_script_exit=1,raw_postbuild_export_count_check_failed=True,
    erroneous_expected_cci_exports=4,actual_cci_exports=5,all_five_equal_original363=True,
    corrected_by_cached_artifact_inspection=True,make_targets_completed_before_postbuild_check=True,
    build_or_camera_not_replayed=True,jobs=2,diagnostics=diagnostics,build_log_sha256=sha(log),
    candidate_sha256=manifest['candidate_sha256'],private_header_sha256=manifest['header_sha256'],
    module_bytes=ko.stat().st_size,module_sha256=sha(ko),intree=info('intree'),vermagic=info('vermagic'),depends=info('depends'),
    imported_symbols=len(imports),all_imports_in_original363_symvers=True,
    image363_input_config_sha256=hashlib.sha256(config).hexdigest(),configuration_differences_from_image363=diff,
    api_headers_equal_image363=headers,shared_inputs_and_source_unchanged=True,
    private_modpost_vmlinux_bytes=(build/'vmlinux.o').stat().st_size,no_shared_vmlinux_link=True,
    unchanged_cci_provider_built_for_modpost_only=True,cci_provider_to_install=False,
    free_bytes=shutil.disk_usage(shared).free,image_or_rootfs_or_full_modules_built=False,
    sdk_or_phone_accessed=False,installed_or_loaded=False)
(HERE/'module-build-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
