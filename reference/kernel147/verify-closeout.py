from pathlib import Path
import tarfile,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel147'); ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
path=out / 'closeout-private.tar.gz'
with tarfile.open(path) as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1); assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert 'ARCHIVE_SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest() in (out / 'closeout-host-private.log').read_text()
with tarfile.open(out / 'preflash-private.tar.gz') as t:
    member=next(m for m in t if m.name.endswith('partition-check.sha256'))
    before=t.extractfile(member).read().decode().splitlines()
current=data['partitions-private.sha256'].decode().splitlines()
for dev in ['/dev/sde11','/dev/sda2']:
    assert next(x for x in before if x.endswith('  '+dev)) in current
build=json.loads((ref / 'build-package-validation.json').read_text())
assert build['logdump_sha256']+'  /dev/sde32' in current
assert data['boot-id-private.txt'].decode().strip()==(out / 'embedded-boot-id-private.txt').read_text().strip()
report=json.loads(data['closeout-validation.json'])
report.update(partition_readback_pass=True,boot_and_persist_unchanged=True,archive_members_verified=True)
(ref / 'closeout-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_CLOSEOUT_ARCHIVE_AND_PARTITIONS_VERIFIED')
