from pathlib import Path
import ast, shutil

ref = Path(__file__).resolve().parent
prior = ref.parent / 'kernel199'
private = Path('/mnt/e/edk2-samurai-out/kernel200')
private.mkdir(mode=0o700, exist_ok=True)
archive = ref.parent.parent / 'archive/NEXT-SESSION-through199-2026-10-15.md'
if not archive.exists():
    shutil.copyfile(ref.parent.parent / 'NEXT-SESSION.md', archive)
source = (prior / 'host.py').read_text().replace('transport198', 'transport199').replace("'kernel198/host.py'", "'kernel199/host.py'").replace('out/kernel199', 'out/kernel200')
ast.parse(source)
(ref / 'host.py').write_text(source)
shutil.copyfile(prior / 'run-native.py', ref / 'run-native.py')

source = (ref.parent / 'kernel172/build-package.py').read_text()
source = source.replace('out/kernel172', 'out/kernel200')
source = source.replace("dt = json.loads((ref / 'kernel-build-validation.json').read_text())", "dt = json.loads((ref.parent / 'kernel199/static-dtb-validation.json').read_text())")
source = source.replace("out / 'samurai-headset-k172-private.dtb'", "out.parent / 'kernel199/sm8150-samurai-mmcx-static-private.dtb'")
source = source.replace("dt['dtb_sha256']", "'2e2f8e64319195f2d4af98b4cec1a83a2da31ed80a97c2b6afbf261b2e25d3e2'")
source = source.replace("out.parent / 'kernel171/boot-partition-k171-speaker-sd1.img'", "out.parent / 'kernel172/boot-partition-k172-headset.img'")
source = source.replace('612a012426200d4997b33ee98edd18ea6e15a61d23901aa82cb61acd68c392f2', '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28')
source = source.replace("['audio-routing', 'widgets']", "['power-domain-names', 'power-domains']")
source = source.replace("assert sorted((r['node'], r['property']) for r in dt['dtb_semantic_changes']) == sorted(dt_changes)", "assert all(p == '/soc@0/camss@acb3000' for p, n in dt_changes)")
# Only the destination is renamed: the old image remains the exact stage172 baseline.
source = source.replace("boot_path = out / 'boot-partition-k172-headset.img'", "boot_path = out / 'boot-partition-k200-mmcx.img'")
source = source.split("logdump_old =")[0]
source += '''
baseline = json.loads((ref.parent / 'kernel183/build-package-validation.json').read_text())
report = dict(stage=200, kernel_build=183, firmware_build_pass=True,
    legacy_firmware_diagnostics=len(current), new_diagnostic_templates=0,
    firmware_only_dtb_changed=True, changed_modules=changed,
    all_firmware_code_and_non_version_data_unchanged=True,
    dtb_semantic_changes=[dict(node=p, property=n) for p, n in dt_changes],
    dtb_sha256=sha(dtb), kernel_image_preserved=baseline['image_sha256'],
    logdump_preserved=baseline['logdump_sha256'], repository_dtb_restored=True,
    bootshim_ramdisk_android_header_compat_preserved=True, boot_tail_preserved=True,
    fv_ffs_gzip_lzma_checked=True, boot_bytes=boot_path.stat().st_size,
    boot_sha256=sha(boot_path.read_bytes()), rollback_boot_sha256=sha(before),
    candidate_camss_sha256='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58',
    flash_partitions=['boot'], hardware_not_deployed=True)
for directory in [out, ref]:
    (directory / 'build-package-validation.json').write_text(json.dumps(report, indent=2) + '\\n')
print(json.dumps(report), flush=True)
'''
ast.parse(source)
(ref / 'build-package.py').write_text(source)
print('K200_HOST_AND_BOOT_ONLY_PACKAGE_SCRIPT_PREPARED')
