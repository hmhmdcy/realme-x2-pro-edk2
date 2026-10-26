from pathlib import Path
import hashlib,json,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel238')
assert json.loads((R/'r14-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
assert json.loads((R/'gain-helper-test-validation.json').read_text())['results']['r14']['exit']==0
prefix=Path('/home/cy122/x2pro-linux/libcamera238-r14-qa-prefix');repo=P/'camera-forward-repo-r14';manifest=json.loads((repo/'package-manifest.json').read_text())
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
files={name:item for package in manifest['packages'] if package['name'] in selected for name,item in package['files'].items()}
assert len([p for p in manifest['packages'] if p['name'] in selected])==7
target=P/'r14-runtime-candidate-private.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz',dereference=False) as archive:
 for name,item in files.items():archive.add(prefix/name,arcname=name,recursive=False)
lock=dict(stage=238,files=files,bundle_bytes=target.stat().st_size,bundle_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),runtime_package_names=sorted(selected))
(P/'candidate-runtime-lock-private.json').write_text(json.dumps(lock,indent=2)+'\n')
print(json.dumps(dict(stage=238,seven_runtime_packages_bundled=True,payload_files=len(files),full13_packages_retained=True,phone_not_modified_yet=True)))
