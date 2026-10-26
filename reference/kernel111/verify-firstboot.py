from pathlib import Path
import hashlib, json, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel111')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def read_archive(name, expected):
    p = out/name
    assert sha(p) == expected
    with tarfile.open(p) as t:
        result = {}
        for m in t:
            if m.isfile():
                key = str(Path(m.name))
                assert not key.startswith('/') and '..' not in Path(key).parts
                result[key] = t.extractfile(m).read()
        return result
files = read_archive('firstboot-diagnostic.tar',
    'bbdbfab7718590b713d0ce0f0f4902cf274c05bbf0810be4127f09aa89f19eca')
for line in files['SHA256SUMS'].decode().splitlines():
    expected, name = line.split('  ', 1)
    assert hashlib.sha256(files[name]).hexdigest() == expected
assert files['state.txt'].decode().splitlines()[-1] == '512'
assert not any(' f2fs ' in l for l in files['mounts.txt'].decode().splitlines())
hashes = dict(line.split()[::-1] for line in files['partition-check.sha256'].decode().splitlines())
candidate = json.loads((out/'candidate-validation.json').read_text())
assert hashes['/dev/sde11'] == candidate['boot_sha256']
assert hashes['/dev/sde32'] == candidate['logdump_sha256']
assert hashes['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
checks = read_archive('ro-validation.tar',
    '47537e007c7b2c3999e4b25557d2a361e0781c3a4e1d50b1830f31e5df5379e4')
for name, count in [('k111-source-check.txt',4),('k111-nv-check.txt',6)]:
    lines = checks[name].decode().splitlines()
    assert len(lines) == count and all(l.endswith(': OK') for l in lines)
report = dict(kernel_build=111,flashed_boot_and_logdump_verified=True,
    firstboot_reached_diagnostic_initramfs=True,firstboot_persistent_root=False,
    taint=512,early_warning_missing_from_overwritten_ring=True,
    usb_ssh_recovered_manually=True,userdata_ro_validation_pass=True,
    stock_source_partitions_unchanged=True,nv_sources_unchanged=True,persist_unchanged=True,
    slpi_started=False,slpi_sensor_samples=False,physical_phosh_109_user_confirmed=True,
    goal_complete=False)
(out/'firstboot-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL111_FAILED_BOOT_EVIDENCE_AND_READ_ONLY_STORAGE_CHECKS_VERIFIED')
