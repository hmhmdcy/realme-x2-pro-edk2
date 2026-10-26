from pathlib import Path
import hashlib,json,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
assert json.loads((R/'r15-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
helper=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera239-r15-built/src/libcamera-v0.7.2/src/ipa/libipa/camera_sensor_helper.cpp');assert hashlib.sha256(helper.read_bytes()).hexdigest()==json.loads((R.parent/'kernel238/helper-source-validation.json').read_text())['source_files']['src/ipa/libipa/camera_sensor_helper.cpp']
prefix=Path('/home/cy122/x2pro-linux/libcamera239-r15-qa-prefix');repo=P/'camera-forward-repo-r15';manifest=json.loads((repo/'package-manifest.json').read_text())
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
files={name:item for package in manifest['packages'] if package['name'] in selected for name,item in package['files'].items()}
assert len([p for p in manifest['packages'] if p['name'] in selected])==7
target=P/'r15-runtime-candidate-private.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz',dereference=False) as archive:
 for name,item in files.items():archive.add(prefix/name,arcname=name,recursive=False)
lock=dict(stage=239,files=files,bundle_bytes=target.stat().st_size,bundle_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),runtime_package_names=sorted(selected))
(P/'candidate-runtime-lock-private.json').write_text(json.dumps(lock,indent=2)+'\n')
print(json.dumps(dict(stage=239,seven_runtime_packages_bundled=True,payload_files=len(files),full13_packages_retained=True,phone_not_modified_yet=True)))
