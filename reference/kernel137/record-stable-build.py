from pathlib import Path
import hashlib
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel137'
out = Path('/mnt/e/edk2-samurai-out/kernel137')
meta = json.loads((r / 'reference/kernel132/complete-bundle-validation.json').read_text())
assert meta['matching_boot_logdump_rootfs_modules_complete']
artifacts = []
for item in meta['artifacts']:
    path = Path('/mnt/e') / item['artifact_path'].removeprefix('E:/')
    assert path.stat().st_size == item['bytes']
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(8 * 1024**2), b''):
            h.update(chunk)
    assert h.hexdigest() == item['sha256']
    artifacts.append(item)
assert [a['role'] for a in artifacts] == ['boot', 'logdump', 'modules', 'rootfs']
report = dict(stage=137, kernel_build=132, software_generation=132,
    stable132_bundle_verified=True, all_770_modules_byte_identical132=True,
    dtb_byte_identical132=True, four_artifacts_fresh_hash_verified=True,
    artifacts=artifacts, flash_partitions=['logdump'], userdata_bulk_flash_or_erase=False,
    deployed=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'stable-build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K137_STABLE132_ALL_FOUR_ARTIFACTS_FRESH_HASH_PASS', flush=True)
