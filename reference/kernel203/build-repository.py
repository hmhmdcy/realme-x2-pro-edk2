from pathlib import Path
import hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel203');linux=Path('/home/cy122/x2pro-linux/samurai-packages203')
locations=json.loads((private/'build-locations-private.json').read_text());signing=json.loads((private/'signing-locations-private.json').read_text())
apk='/home/cy122/pmos-samurai-rootfs01/work/apk.static';key=signing['private_key'];verification=locations['verification_keys'];first=Path(locations['first_build']);second=Path(locations['second_build'])
for index,directory in enumerate([first,second]):
 target=directory/'packages.adb';assert not target.exists()
 command=[apk,'--keys-dir',verification,'mkndx','--compression','deflate:9','--sign-key',key,'--pkgname-spec','${name}-${version}.apk','--description','Realme X2 Pro validated GNSS backend203','--output',str(target),*[str(p) for p in sorted(directory.glob('*.apk'))]]
 result=subprocess.run(command,capture_output=True,check=True);(private/('mkndx-'+str(index)+'-private.log')).write_bytes(result.stdout+result.stderr)
 subprocess.run([apk,'--keys-dir',verification,'verify',str(target)],capture_output=True,check=True)
assert (first/'packages.adb').read_bytes()==(second/'packages.adb').read_bytes()
original=next(first.glob('modemmanager-1*.apk'))
untrusted=subprocess.run([apk,'--keys-dir','/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys','verify',str(original)],capture_output=True);assert untrusted.returncode!=0
(private/'untrusted-package-rejected-private.log').write_bytes(untrusted.stdout+untrusted.stderr)
tampered=private/'tampered-package-test-private.apk';assert not tampered.exists();raw=bytearray(original.read_bytes());raw[len(raw)//2]^=1;tampered.write_bytes(raw)
verify=subprocess.run([apk,'--keys-dir',verification,'verify',str(tampered)],capture_output=True)
(private/'tampered-verify-private.log').write_bytes(verify.stdout+verify.stderr)
destination=linux/'tampered-extraction-test';assert not destination.exists();destination.mkdir()
extract=subprocess.run([apk,'--keys-dir',verification,'extract','--destination',str(destination),str(tampered)],capture_output=True);assert extract.returncode!=0
(private/'tampered-extract-private.log').write_bytes(extract.stdout+extract.stderr)
r=dict(stage=203,signed_repository_verified=True,repository_two_builds_byte_identical=True,index_sha256=hashlib.sha256((first/'packages.adb').read_bytes()).hexdigest(),untrusted_key_rejected=True,tampered_package_verify_rejected=verify.returncode!=0,tampered_payload_extraction_rejected=True,relative_package_names_used=True)
(here/'repository-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
