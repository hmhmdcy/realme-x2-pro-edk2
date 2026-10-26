from pathlib import Path
import hashlib,json,tarfile
import host

here=Path(__file__).resolve().parent
native=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204r2-runtime/boot-id-private.txt').read_bytes()
health=json.loads((root/'k204r2-final-health-r3/summary.json').read_text());assert health['same_verified_current_boot'] and health['ssc_automatic_start_and_real_readiness_passed']
out=root/'k204r2-export-final';assert not out.exists();out.mkdir(mode=0o700)
sources=sorted(p for p in root.glob('k204r2-*') if p.is_dir() and p!=out)+[root/'gnss-assist',Path('/run/samurai-ssc')]
manifest={}
for source in sources:
 for p in sorted(source.rglob('*')):
  if not p.is_file() or p.is_symlink():continue
  rel=Path('run-ssc')/p.relative_to(source) if source==Path('/run/samurai-ssc') else p.relative_to(root)
  target=out/rel;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(p,target);manifest[str(rel)]=hashlib.sha256(target.read_bytes()).hexdigest()
(out/'live-private.dtb').write_bytes(Path('/sys/firmware/fdt').read_bytes());manifest['live-private.dtb']=hashlib.sha256((out/'live-private.dtb').read_bytes()).hexdigest()
(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=Path('/tmp/k204-final-evidence-private.tar.gz');assert not archive.exists();subprocess.run(['tar','-C',str(out),'-czf',str(archive),'.'],check=True)
print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=60);r=json.loads(p.stdout);target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists();host.download('/tmp/k204-final-evidence-private.tar.gz',target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256']
with tarfile.open(target,'r:gz') as archive:
 files={m.name.removeprefix('./'):m for m in archive.getmembers() if m.isfile()};manifest=json.load(archive.extractfile(files['manifest-private.json']));assert len(manifest)==r['files'] and len(files)==len(manifest)+1
 for name,digest in manifest.items():assert hashlib.sha256(archive.extractfile(files[name]).read()).hexdigest()==digest
report=dict(stage=204,reboot_cycle=2,private_files=r['files'],archive_and_every_member_verified=True,private_fingerprint_omitted=True)
(here/'archive-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for remote,name in [('k204r2-final-health-r3/summary.json','native-health-validation.json')]:
 target=host.PRIVATE/name;host.download('/var/lib/samurai/'+remote,target);(here/name).write_bytes(target.read_bytes())
print(json.dumps(report))
