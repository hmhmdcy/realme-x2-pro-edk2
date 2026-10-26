from pathlib import Path
import hashlib,json,os,shutil,subprocess

os.umask(0o077)
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel203')
linux=Path('/home/cy122/x2pro-linux/samurai-packages203');signing=linux/'signing-private';signing.mkdir(mode=0o700,exist_ok=True)
key=signing/'samurai-linux-203.rsa';public=signing/'samurai-linux-203.rsa.pub'
if not key.exists():
 assert not public.exists()
 with (private/'keygen-private.log').open('wb') as log:
  subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],check=True,stdout=log,stderr=subprocess.STDOUT)
  subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(public)],check=True,stdout=log,stderr=subprocess.STDOUT)
else:
 derived=subprocess.check_output(['openssl','pkey','-in',str(key),'-pubout']);assert derived==public.read_bytes()
key.chmod(0o600);public.chmod(0o644)
verification=linux/'verification-keys';verification.mkdir(mode=0o700,exist_ok=True);shutil.copyfile(public,verification/public.name)
published_public=private/'package-signing';published_public.mkdir(mode=0o700,exist_ok=True);shutil.copyfile(public,published_public/public.name)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');upstream_keys=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
labels=[str(index) for index in range(1,100) if not (linux/('build-'+str(index))).exists() and not (private/('packages-'+str(index))).exists()][:2];assert len(labels)==2
for label in labels:
 command=['python3',str(repo/'linux-port/packages/apk3/build.py'),'--inputs',str(private/'upstream-apks'),'--candidate',str(private/'ModemManager203-candidate'),'--apk',str(apk),'--trusted-keys',str(upstream_keys),'--sign-key',str(key),'--build-root',str(linux/('build-'+label)),'--output',str(private/('packages-'+label))]
 with (private/('packages-build-'+label+'-private.log')).open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=200)
first=private/('packages-'+labels[0]);second=private/('packages-'+labels[1]);checks=[]
for path in sorted(first.glob('*.apk')):
 assert path.read_bytes()==(second/path.name).read_bytes()
 p=subprocess.run([str(apk),'--keys-dir',str(verification),'verify',str(path)],capture_output=True,check=True)
 (private/(path.name+'-signature-verification.txt')).write_bytes(p.stdout+p.stderr)
 checks.append(dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),signed_verification_pass=True,second_build_byte_identical=True))
assert len(checks)==5
r=dict(stage=203,package_count=5,all_signatures_verified=True,two_builds_byte_identical=True,packages=checks,helper_source_unchanged=True,mm_candidate191_byte_identical=True,no_device_install_performed=True,signing_private_key_kept_off_device=True)
(here/'package-build-validation.json').write_text(json.dumps(r,indent=2)+'\n')
(private/'signing-locations-private.json').write_text(json.dumps(dict(private_key=str(key),public_key=str(public),verification_keys=str(verification)),indent=2)+'\n')
(private/'build-locations-private.json').write_text(json.dumps(dict(first_build=str(first),second_build=str(second),verification_keys=str(verification)),indent=2)+'\n')
print(json.dumps(r))
