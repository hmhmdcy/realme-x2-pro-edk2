"""Sign a small local index without altering the official APK signatures."""
from pathlib import Path
import json
import subprocess

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel240')
manifest=json.loads((P/'snapshot-distro-manifest-private.json').read_text());assert len(manifest['packages'])==14
repo=P/'snapshot-distro-apks';index=repo/'packages.adb';assert not index.exists()
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
keys=P.parent/'kernel214/phone-trusted-public-keys'
key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
args=[str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(key),
 '--pkgname-spec','${name}-${version}.apk','--description','Realme X2 Pro Snapshot51 distribution application candidate',
 '--output',str(index),*[str(repo/p['file']) for p in manifest['packages']]]
result=subprocess.run(args,capture_output=True,timeout=45)
(P/'snapshot-index-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
result=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(index)],capture_output=True,timeout=15)
(P/'snapshot-index-verify-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
report=dict(stage=240,local_index_signed_with_existing_trusted_package_key=True,
 official_fourteen_apk_signatures_preserved=True,no_signing_key_transferred_to_phone=True,
 package_count=14,index_bytes=index.stat().st_size,no_package_installation=True)
(R/'snapshot-index-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
