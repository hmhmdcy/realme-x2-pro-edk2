from pathlib import Path
import hashlib,importlib.util,json,tarfile

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_r2',here/'reboot-r2/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
native=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k202r2-export-final';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202r2-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k202r2-final-health/summary.json').read_text())['same_verified_new_boot']
sources=sorted(p for p in root.glob('k202r2-*') if p.is_dir() and p!=out)+[root/'gnss-assist',root/'k202-helper-deploy']
manifest={}
for source in sources:
 for p in sorted(source.rglob('*')):
  assert not p.is_symlink()
  if not p.is_file():continue
  relative=p.relative_to(root);target=out/relative;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(p,target);manifest[str(relative)]=hashlib.sha256(target.read_bytes()).hexdigest()
(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=Path('/tmp/k202-final-cycle-private.tar.gz');subprocess.run(['tar','-C',str(out),'-czf',str(archive),'.'],check=True)
print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=60);report=json.loads(p.stdout)
target=host.PRIVATE/'final-cycle-evidence-private.tar.gz';assert not target.exists();host.download('/tmp/k202-final-cycle-private.tar.gz',target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['sha256']
with tarfile.open(target,'r:gz') as archive:
    files={m.name.removeprefix('./'):m for m in archive.getmembers() if m.isfile()}
    manifest=json.load(archive.extractfile(files['manifest-private.json']))
    assert len(manifest)==report['files'] and len(files)==len(manifest)+1
    for name,digest in manifest.items():assert hashlib.sha256(archive.extractfile(files[name]).read()).hexdigest()==digest
(here/'final-cycle-archive-validation.json').write_text(json.dumps(dict(stage=202,private_files=report['files'],archive_and_every_member_verified=True,private_fingerprint_omitted=True),indent=2)+'\n')
print(json.dumps(dict(stage=202,private_files=report['files'],archive_and_every_member_verified=True)))
