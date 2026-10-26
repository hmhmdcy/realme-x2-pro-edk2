"""Verify signed outputs and stage the packages needed by actual consumers."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys'
signing_key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
repository=host.PRIVATE/'runtime-repository';repository.mkdir(mode=0o700,exist_ok=True)
prefix=host.PRIVATE/'package-prefix';prefix.mkdir(mode=0o700,exist_ok=True)
runtime={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
records=[]
for p in [*sorted((storage.candidate().parent/'packages342-r27').rglob('*.apk')),*sorted((storage.candidate().parent/'packages-config342-r27').rglob('*.apk'))]:
 q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(p)],capture_output=True,timeout=20)
 (host.PRIVATE/(p.name+'-verify.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,p.name
 with tarfile.open(p,'r:gz',ignore_zeros=True) as tar:
  fields={}
  for line in tar.extractfile('.PKGINFO').read().decode().splitlines():
   if ' = ' in line:k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
  name=fields['pkgname'][0];version=fields['pkgver'][0]
  assert version==('0.1.0-r22' if name.startswith('samurai-camera-') else '99990.7.2-r27')
  records.append(dict(name=name,version=version,arch=fields['arch'][0],file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),runtime=name in runtime))
  if name in runtime:
   for member in tar.getmembers():
    rel=member.name.removeprefix('./').rstrip('/')
    if not rel or rel.startswith('.'):continue
    assert rel.startswith(('usr/','etc/')) or rel in ['usr','etc'],rel
    assert not rel.startswith('/') and '..' not in Path(rel).parts
    dest=prefix/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if member.isdir():dest.mkdir(exist_ok=True);dest.chmod(member.mode)
    elif member.issym():
     if dest.is_symlink():dest.unlink()
     assert not dest.exists(),str(dest)
     dest.symlink_to(member.linkname)
    elif member.isfile():dest.write_bytes(tar.extractfile(member).read());dest.chmod(member.mode)
   target=repository/'forward'/p.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target)
rollback=repository/'rollback';rollback.mkdir(exist_ok=True)
for p in (host.PRIVATE.parent/'kernel321/runtime-repository/forward').glob('*.apk'):
 shutil.copyfile(p,rollback/p.name)
for kind in ['forward','rollback']:
 directory=repository/kind
 q=subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(signing_key),
  '--pkgname-spec','${name}-${version}.apk','--description','CAMSS342 '+kind,'--output',str(directory/'packages.adb'),*[str(p) for p in sorted(directory.glob('*.apk'))]],capture_output=True,timeout=60)
 (host.PRIVATE/(kind+'-index.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0
 q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(directory/'packages.adb')],capture_output=True,timeout=20);assert q.returncode==0
new_ipa=prefix/'usr/lib/libcamera/ipa/ipa_camss_vfe.so'
assert new_ipa.is_file() and new_ipa.with_name(new_ipa.name+'.sign').is_file()
assert (prefix/'usr/libexec/libcamera/camss_ipa_proxy').is_file()
assert (prefix/'usr/lib/gstreamer-1.0/libgstlibcamera.so').is_file()
assert all((prefix/'usr/share/libcamera/ipa/camss-vfe'/(m+'.yaml')).is_file() for m in ['s5kgw1','imx471','imx319','s5k3m5'])
build=storage.candidate()/'src/libcamera-v0.7.2/output'
options=json.loads((build/'meson-info/intro-buildoptions.json').read_text())
configured={x['name']:x['value'] for x in options if x['name'] in ['pipelines','ipas','gstreamer','pycamera','qcam','v4l2']}
assert len(list((prefix/'usr/lib/libcamera/ipa').glob('*.so')))==6
candidate=SDK/'candidate342-r27';candidate.mkdir(exist_ok=True);assert not any(candidate.iterdir())
subprocess.run(['mount','--bind',str(prefix),str(candidate)],check=True,capture_output=True)
try:
 with storage.sdk_candidate():
  verify='/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify'
  q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH=/candidate342-r27/usr/lib',verify,
   '/candidate342-r27/usr/lib/libcamera/ipa/ipa_camss_vfe.so'],capture_output=True,timeout=30)
finally:subprocess.run(['umount',str(candidate)],check=True,capture_output=True)
(host.PRIVATE/'new-ipa-signature.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and b'IPA module signature is valid' in q.stdout
manifest=dict(stage=342,packages=records,configuration=configured,all_prior_feature_packages_preserved=True,new_ipa_present=True,signed_runtime_repository=True,installed=False)
manifest['new_ipa_signature_verified_against_packaged_core']=True
(HERE/'package-artifact-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
(host.PRIVATE/'runtime-records.json').write_text(json.dumps([r for r in records if r['runtime']],indent=2)+'\n')
print(json.dumps({'packages':len(records),'runtime_packages':sum(r['runtime'] for r in records),'configuration':configured,'ipa_modules':6}))
