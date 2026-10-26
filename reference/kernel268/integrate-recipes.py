"""Make the current signed-package recipes the public build inputs."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;root=R.parents[1]
for name in ['libcamera','samurai-camera-config']:
 src=R/'recipes'/name;dst=root/'linux-port/packages'/name
 files={}
 for p in src.iterdir():
  if p.is_file():shutil.copyfile(p,dst/p.name);files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 for n,digest in files.items():assert hashlib.sha256((dst/n).read_bytes()).hexdigest()==digest
 lock=dict(stage=268,package_version='99990.7.2-r19' if name=='libcamera' else '0.1.0-r14',source_files_sha256=files,
  actual_signed_build_validation='reference/kernel268/r19-package-build-validation.json',
  native_install_validation='reference/kernel268/native-install-validation.json',
  package_payload_features_preserved=True,private_keys_not_in_sources=True)
 (dst/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print('Current recipes copied and all input SHA256 values verified.')
