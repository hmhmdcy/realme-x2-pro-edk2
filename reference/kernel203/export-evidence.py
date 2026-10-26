from pathlib import Path
import hashlib,json,tarfile
import host

here=Path(__file__).resolve().parent
native=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k203-export-final';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
report=json.loads((root/'k203-final-health/summary.json').read_text());assert report['same_boot202r2'] and report['new_reboot_not_performed']
sources=sorted(p for p in root.glob('k203-*') if p.is_dir() and p!=out)+[root/'gnss-assist']
manifest={}
for source in sources:
 for p in sorted(source.rglob('*')):
  if p.is_symlink():continue
  if not p.is_file():continue
  relative=p.relative_to(root);target=out/relative;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(p,target);manifest[str(relative)]=hashlib.sha256(target.read_bytes()).hexdigest()
snapshot=out/'installed-repository';snapshot.mkdir(mode=0o700)
for p in [root/'packages/gnss-203/package-manifest.json',root/'packages/gnss-203/packages.adb',Path('/etc/apk/keys/samurai-linux-203.rsa.pub'),Path('/etc/apk/repositories.d/50-samurai-gnss.list')]:
 target=snapshot/p.name;shutil.copyfile(p,target);manifest[str(target.relative_to(out))]=hashlib.sha256(target.read_bytes()).hexdigest()
(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=Path('/tmp/k203-evidence-private.tar.gz');assert not archive.exists();subprocess.run(['tar','-C',str(out),'-czf',str(archive),'.'],check=True)
print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=90);report=json.loads(p.stdout)
target=host.PRIVATE/'evidence-private.tar.gz';assert not target.exists();host.download('/tmp/k203-evidence-private.tar.gz',target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['sha256']
with tarfile.open(target,'r:gz') as archive:
 files={m.name.removeprefix('./'):m for m in archive.getmembers() if m.isfile()}
 manifest=json.load(archive.extractfile(files['manifest-private.json']));assert len(manifest)==report['files'] and len(files)==len(manifest)+1
 for name,digest in manifest.items():assert hashlib.sha256(archive.extractfile(files[name]).read()).hexdigest()==digest
r=dict(stage=203,private_files=report['files'],archive_and_every_member_verified=True,private_fingerprint_omitted=True,downloaded_over_authenticated_current_boot_wifi=True)
(here/'archive-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
