from pathlib import Path
import hashlib, json, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel115')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def read(path):
    with tarfile.open(path) as t:
        data = {}
        for m in t:
            assert not m.issym() and not m.islnk()
            if not m.isfile(): continue
            name = m.name.removeprefix('./')
            assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in data
            data[name] = t.extractfile(m).read()
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    return data

archive = out / 'preflash.tar'
assert sha(archive) == '91dd19fbf82664b0e6dca11331bdb84db48a6d154c1df83cd7c7af67c1ebcad3'
data = read(archive)
old = read(out.parent / 'kernel112/layout-after.tar')
for dev in ('sda','sdb','sdc','sdd','sde','sdf'):
    for suffix in ('geometry','head','tail'):
        name = f'{dev}.{suffix}'
        assert data[name] == old[name], name
assert b'#113 SMP PREEMPT' in data['uname.txt']
assert data['state.txt'].splitlines()[-1] == b'512'
assert b'/dev/sda16 / f2fs rw' in data['mounts.txt'] and b' /run tmpfs rw' in data['mounts.txt']
for name, count in [('nv-check.txt',6),('source-check.txt',4)]:
    lines = data[name].decode().splitlines()
    assert len(lines) == count and all(x.endswith(': OK') for x in lines)
parts = dict(line.split('  ')[::-1] for line in data['partition-check.sha256'].decode().splitlines())
assert parts['/dev/sde11'] == sha(out.parent / 'kernel113/boot-partition-k113.img')
assert parts['/dev/sde32'] == sha(out.parent / 'kernel113/logdump-k113-sensor-power.img')
assert parts['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
# Boot guards stay in private storage; never print or publish the value.
boot = data['boot-id-private.txt'].decode().strip()
assert len(boot) == 36 and all(c in '0123456789abcdef-' for c in boot)
guard = out / 'source-boot-id-private.txt'
if guard.exists(): assert guard.read_text().strip() == boot
else: guard.write_text(boot + '\n')
report = dict(preflash_audit_pass=True, live_backups_match=True, kernel_build=113,
              nv_sources_unchanged=True, persist_unchanged=True, gpt_18_unchanged=True,
              sensor_source_partitions_unchanged=True, taint=512,
              archive_sha256=sha(archive), before_boot_sha256=parts['/dev/sde11'],
              before_logdump_sha256=parts['/dev/sde32'])
(out / 'preflash-validation.json').write_text(json.dumps(dict(report,boot_id=boot),indent=2)+'\n')
(ref / 'preflash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL115_FRESH_PREFLASH_BOOT_LOGDUMP_GPT18_NV6_SOURCE4_PERSIST_AUDIT_PASS')
