from pathlib import Path
import hashlib,json,host

here=Path(__file__).resolve().parent;locations=json.loads((host.PRIVATE/'build-locations-private.json').read_text());directory=Path(locations['first_build']);key=host.PRIVATE/'package-signing/samurai-linux-203.rsa.pub'
repo='/var/lib/samurai/packages/gnss-203';staging='/var/lib/samurai/k203-packages'
host.ssh('python3 -',input=b"from pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k203-baseline/boot-id-private.txt').read_bytes()\nfor p in ['/var/lib/samurai/packages/gnss-203','/var/lib/samurai/k203-packages']:\n assert not Path(p).exists()\n Path(p).mkdir(mode=0o700,parents=True)\n")
for path in sorted(directory.glob('*.apk')):host.upload(path,repo+'/'+path.name)
for name in ['packages.adb','package-manifest.json']:host.upload(directory/name,repo+'/'+name)
host.upload(key,staging+'/'+key.name)
report=dict(stage=203,package_files=5,repository=repo,only_public_verification_key_staged=True,private_signing_key_not_uploaded=True,index_sha256=hashlib.sha256((directory/'packages.adb').read_bytes()).hexdigest(),public_key_sha256=hashlib.sha256(key.read_bytes()).hexdigest())
(host.PRIVATE/'staging-manifest-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({name:value for name,value in report.items() if name!='public_key_sha256'}))
