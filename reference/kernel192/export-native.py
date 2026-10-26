from pathlib import Path
import os,hashlib,json,tarfile
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai');out=root/'k192-export';out.mkdir(mode=0o700)
files=[p for directory in sorted(root.glob('k192-*')) if directory.is_dir() and directory!=out for p in sorted(directory.rglob('*')) if p.is_file() and not p.is_symlink()]
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=out/'evidence-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
 tar.add(out/'manifest-private.json',arcname='manifest-private.json')
record=dict(stage=192,files=len(files),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(out/'export-summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
