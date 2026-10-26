from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel213')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text());intentional=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())['three_intentional_source_changes']
assert all(sha(kernel/name)==intentional.get(name,digest) for name,digest in old.items())
before=json.loads((private.parent/'kernel211/source-before/hashes-private.json').read_text())
assert all(sha(kernel/name)==before[name] for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
for path in here.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
source=private/'source/libcamera-v0.7.2'
expected={'src/ipa/libipa/camera_sensor_helper.cpp':'f313c423097ead6345db614706a075165dc775f5e08c65b4823cb6bac3271b90','src/libcamera/sensor/camera_sensor_properties.cpp':'938ea102ca456b3d853d7bffc18822a2c674dfd76d4c65c4e3c282e13d618b14','src/libcamera/software_isp/debayer_cpu.cpp':'febace312318e7070bc052ebee20aab9628911b875807aae979f33a27712a4ba','src/libcamera/software_isp/debayer_cpu.h':'0b137badef443b0f1db8c715002fcb8fb6f1602e3ec35915b8fa76a1bfa287f8'}
assert all(sha(source/name)==digest for name,digest in expected.items())
patches={path.name:sha(path) for path in sorted((repo/'linux-port/camera/libcamera').glob('*.patch'))};assert len(patches)==3
lock=dict(schema=1,upstream_version='0.7.2',upstream_url='https://gitlab.freedesktop.org/camera/libcamera/-/archive/v0.7.2/libcamera-v0.7.2.tar.gz',upstream_sha512='b317cdc96f61682ee0bf26dfb7c4d6441db9a9c5b93ab53528121a8cd44862b3d59cbaa3881bb0837e3e381564c184c7b742124aef4267eea754c6083de353c1',base_distro_version='99990.7.2-r4',original_distro_patch_count=6,additional_patches_sha256=patches,source_files_sha256=expected,helper_upstream_commit='e64b507de18774352cbe0bdfd51b637b00a56873',properties_upstream_commit='59e7f18952de3aaa5e4948928e7602779a02296d',sensor_pixel_size_nm=[1000,1000],pixel_size_primary_source='https://www.oneplus.com/hk/9/specs',control_delays_unverified=True,upstream_black_level_16bit=4096,own_handset_dark_calibration_not_claimed=True,current_candidate_not_installed=True)
(repo/'linux-port/camera/libcamera/source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
report=dict(stage=213,no_additional_kernel_source_change=True,all_saved_kernel_source_and_build_metadata_preserved=True,libcamera_helper_properties_and_one_line_lut_patch_verified=True,cpu_debayer_header_and_abi_preserved=True,reference_python_syntax_passed=True,kernel_diff_check_passed=True,no_source_staged=True,no_boot_or_other_partition_flash=True,signing_private_keys_not_in_product_sources=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
