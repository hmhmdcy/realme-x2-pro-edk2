from pathlib import Path
import hashlib,json,tarfile
import host

here=Path(__file__).resolve().parent
native=r'''
from pathlib import Path
import dbus,hashlib,json,os,shutil,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
out=root/'k204-export-first';assert not out.exists();out.mkdir(mode=0o700)
assert json.loads((root/'k204-bt-scan-pm-r2/summary.json').read_text())['passed']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
sources=[p for p in root.glob('k204-*') if p.is_dir() and p!=out]+[root/'gnss-assist',Path('/run/samurai-ssc')]
manifest={}
for source in sources:
 for p in sorted(source.rglob('*')):
  if not p.is_file() or p.is_symlink():continue
  rel=(Path('run-ssc')/p.relative_to(source)) if source==Path('/run/samurai-ssc') else p.relative_to(root)
  target=out/rel;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(p,target);manifest[str(rel)]=hashlib.sha256(target.read_bytes()).hexdigest()
(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=Path('/tmp/k204-first-evidence-private.tar.gz');assert not archive.exists();subprocess.run(['tar','-C',str(out),'-czf',str(archive),'.'],check=True)
print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=60);report=json.loads(p.stdout)
target=host.PRIVATE/'first-boot-evidence-private.tar.gz';assert not target.exists();host.download('/tmp/k204-first-evidence-private.tar.gz',target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['sha256']
with tarfile.open(target,'r:gz') as archive:
 files={m.name.removeprefix('./'):m for m in archive.getmembers() if m.isfile()};manifest=json.load(archive.extractfile(files['manifest-private.json']));assert len(manifest)==report['files'] and len(files)==len(manifest)+1
 for name,digest in manifest.items():assert hashlib.sha256(archive.extractfile(files[name]).read()).hexdigest()==digest
r=dict(stage=204,first_boot_files=report['files'],archive_and_every_member_verified=True,private_fingerprint_omitted=True,failed_boot_ssc_and_initial_bt_test_retained=True)
(here/'first-boot-archive-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
