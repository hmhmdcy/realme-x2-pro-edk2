"""Fully decompress the newly retained build volume; never restore onto a device."""
from pathlib import Path
import hashlib,json,subprocess,time
P=Path('/mnt/e/edk2-samurai-out/cleanup20261019')
archive=P/'kernel118-current-build-volume.ext4.zst'
assert archive.is_file() and not archive.is_symlink()
assert archive.resolve().is_relative_to(P)
digest=hashlib.sha256();size=0
with subprocess.Popen(['zstd','-q','-d','-c',str(archive)],stdout=subprocess.PIPE) as child:
    while block:=child.stdout.read(4*1024**2):digest.update(block);size+=len(block)
    assert child.wait()==0
assert size==21474836480 and digest.hexdigest()=='f4a8328f0a5b2fe32c74695c70846ef4b7a176a98a23cf070c34a1ea4cc5bd96'
result=dict(verified=True,decompressed_bytes=size,sha256=digest.hexdigest(),archive_bytes=archive.stat().st_size,
            archive=str(archive),original_removed=False,read_only_inspection=True,
            old145_archive_differs=True,verified_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
(P/'volume118-verification-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
