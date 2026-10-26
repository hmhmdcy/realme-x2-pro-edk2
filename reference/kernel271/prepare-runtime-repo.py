"""Select seven full-build APKs and create a signed native repository."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tarfile

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel271')
assert json.loads((R/'complete-host-qa-validation.json').read_text())['all_13_package_signatures_and_features_checked']
complete=P/'camera-forward-repo-r20';manifest=json.loads((complete/'package-manifest.json').read_text())
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
packages=[p for p in manifest['packages'] if p['name'] in selected];assert len(packages)==7
out=P/'camera-runtime-repo-r20';out.mkdir(mode=0o700);forward=out/'forward';forward.mkdir(mode=0o700)
for package in packages:shutil.copyfile(complete/package['file'],forward/package['file'])
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=P.parent/'kernel214/phone-trusted-public-keys'
key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
q=subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(key),
 '--pkgname-spec','${name}-${version}.apk','--description','Common camera link-state fix r20',
 '--output',str(forward/'packages.adb'),*[str(p) for p in sorted(forward.glob('*.apk'))]],capture_output=True,timeout=60)
(P/'runtime-index-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(forward/'packages.adb')],capture_output=True,timeout=20)
(P/'runtime-index-verify-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
(out/'forward-manifest.json').write_text(json.dumps(dict(stage=271,packages=packages),indent=2)+'\n')
archive=P/'r20-seven-package-repo-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for p in sorted(out.rglob('*')):
        if p.is_file():tar.add(p,arcname=str(p.relative_to(out)),recursive=False)
report=dict(stage=271,signed_seven_package_repository=True,bytes=archive.stat().st_size,
 sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),packages=[dict(name=x['name'],version=x['version']) for x in packages])
(R/'runtime-repo-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
