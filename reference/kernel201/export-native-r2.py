from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k201-export-r2';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
dirs=[d for d in sorted(root.glob('k201-*')) if d.is_dir() and not d.name.startswith('k201-export')]+[root/'gnss-assist']
files=[p for d in dirs for p in sorted(d.rglob('*')) if p.is_file() and not p.is_symlink()]
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=out/'evidence-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
 tar.add(out/'manifest-private.json',arcname='manifest-private.json')
report=dict(stage=201,files=len(files),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest());(out/'export-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='archive_sha256'}))
