from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel111')
files={}
archive=out/'preflash.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='44c2fa732d670ee121e6c991aa188a21face00ade8edaf346a8023e8c1119b21'
with tarfile.open(archive) as t:
    for m in t:
        if m.isfile():
            p=Path(m.name);assert p.parts[0]=='k111-preflash' and '..' not in p.parts
            files[str(Path(*p.parts[1:]))]=t.extractfile(m).read()
for line in files['SHA256SUMS'].decode().splitlines():
    sha,name=line.split('  ',1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==sha
assert files['boot-id-private.txt'].decode().strip()==(out/'source-boot-id-private.txt').read_text().strip()
assert files['state.txt'].decode().splitlines()[-1]=='0'
hashes=dict(line.split()[::-1] for line in files['boot-logdump-persist.sha256'].decode().splitlines())
audit=json.loads((out/'candidate-validation.json').read_text())
assert hashes['/dev/sde11']==audit['before_boot_sha256']
assert hashes['/dev/sde32']==audit['before_logdump_sha256']
assert hashes['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
for name,count in [('nv-check.txt',6),('k111-sensor-sources-still-unchanged.txt',4),('k111-module-package-check.txt',2)]:
    lines=files[name].decode().splitlines()
    assert len(lines)==count and all(line.endswith(': OK') for line in lines)
assert ' /run tmpfs rw' in files['mounts.txt'].decode()
report=dict(preflash_audit_pass=True,live_backups_match=True,nv_sources_unchanged=True,
            persist_unchanged=True,sensor_source_partitions_unchanged=True,taint=0,
            boot_id=files['boot-id-private.txt'].decode().strip(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(out/'preflash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('FRESH_DEVICE_BACKUPS_NV_PERSIST_MODULES_CHECKPOINT_AUDIT_PASS')
