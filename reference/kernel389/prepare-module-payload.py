"""Separate the small module/FW payload from the boot image transport."""
from pathlib import Path
import hashlib,json,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
manifest=json.loads((P/'deployment-manifest-private.json').read_text());build=json.loads((HERE/'intree-build-validation.json').read_text());mods={r['name']:r for r in build['modules']}
files={}
for row in manifest['modules']:files['modules/'+row['target_relative']]=Path(mods[row['name']]['private_path'])
files['firmware/camera-icp.elf']=P.parent/'kernel352/CAMERA_ICP.elf-private'
stage=dict(manifest);stage['files_sha256']={n:manifest['files_sha256'][n] for n in files};stage['boot_delivered_separately']=True
for n,p in files.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==stage['files_sha256'][n]
metadata=P/'module-stage-manifest-private.json';metadata.write_text(json.dumps(stage,indent=2)+'\n');files['manifest.json']=metadata
archive=P/'modules-firmware-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
with tarfile.open(archive,'r:gz') as tar:
 assert {m.name for m in tar.getmembers()}==set(files)
 for n,p in files.items():assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((HERE/'deployment-package-validation.json').read_text());proof.update(separate_modules_firmware_bytes=archive.stat().st_size,separate_modules_firmware_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),boot_transport_kept_separate=True)
(HERE/'deployment-package-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k.startswith('separate') or k in ['stage','boot_transport_kept_separate','passed']},indent=2))
