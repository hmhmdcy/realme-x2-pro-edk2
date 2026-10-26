from pathlib import Path
from contextlib import contextmanager
import hashlib,json,shutil,subprocess,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;source=storage.candidate();SDK=storage.SDK
assert json.loads((HERE/'package-build-validation.json').read_text())['passed']
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys';signing=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
repository=P/'runtime-repository';prefix=source.parent/'camera420-package-prefix';assert not prefix.exists();prefix.mkdir(mode=0o700)
runtime={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'};records=[]
for package in [*sorted((source.parent/'packages420-r31').rglob('*.apk')),*sorted((source.parent/'packages-config420-r31').rglob('*.apk'))]:
 q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(package)],capture_output=True);(P/(package.name+'-verify.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode
 with tarfile.open(package,'r:gz',ignore_zeros=True) as tar:
  fields={}
  for line in tar.extractfile('.PKGINFO').read().decode().splitlines():
   if ' = ' in line:k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
  name=fields['pkgname'][0];version=fields['pkgver'][0];assert version==('0.1.0-r26' if name.startswith('samurai-camera-') else '99990.7.2-r31')
  records.append(dict(name=name,version=version,arch=fields['arch'][0],file=package.name,bytes=package.stat().st_size,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),runtime=name in runtime))
  if name not in runtime:continue
  for m in tar.getmembers():
   rel=m.name.removeprefix('./').rstrip('/')
   if not rel or rel.startswith('.'):continue
   assert not rel.startswith('/') and '..' not in Path(rel).parts and (rel.startswith(('usr/','etc/')) or rel in ['usr','etc'])
   dest=prefix/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if m.isdir():dest.mkdir(exist_ok=True);dest.chmod(m.mode)
   elif m.issym():
    if dest.is_symlink():dest.unlink()
    assert not dest.exists() and (dest.parent/m.linkname).resolve().is_relative_to(prefix);dest.symlink_to(m.linkname)
   elif m.isfile():dest.write_bytes(tar.extractfile(m).read());dest.chmod(m.mode)
   else:raise RuntimeError('Unexpected package member type')
  directory=repository/'forward';directory.mkdir(parents=True,exist_ok=True);shutil.copyfile(package,directory/package.name)
previous=json.loads((HERE.parent/'kernel391/package-artifact-validation.json').read_text());assert {r['name'] for r in records}=={r['name'] for r in previous['packages']}
assert sum(r['runtime'] for r in records)==7
rollback=repository/'rollback';rollback.mkdir(exist_ok=True);old_records={r['file']:r for r in previous['packages'] if r['runtime']}
for package in (P.parent/'kernel391/runtime-repository/forward').glob('*.apk'):
 assert hashlib.sha256(package.read_bytes()).hexdigest()==old_records[package.name]['sha256'];shutil.copyfile(package,rollback/package.name)
assert len(list(rollback.glob('*.apk')))==7
for kind in ['forward','rollback']:
 directory=repository/kind;q=subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(signing),'--pkgname-spec','${name}-${version}.apk','--description','CAMSS420 '+kind,'--output',str(directory/'packages.adb'),*[str(p) for p in sorted(directory.glob('*.apk'))]],capture_output=True)
 (P/(kind+'-index.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode
 assert not subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(directory/'packages.adb')],capture_output=True).returncode
for model in ['s5kgw1','imx471','imx319','s5k3m5']:assert (prefix/'usr/share/libcamera/ipa/camss-vfe'/(model+'.yaml')).read_bytes()==(HERE/'recipes/samurai-camera-config'/('camss-'+model+'.yaml')).read_bytes()
assert not (prefix/'etc/libcamera/ipa/camss-vfe').exists()
@contextmanager
def bind(actual,slot):
 slot.mkdir(exist_ok=True);assert not any(slot.iterdir()) and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
 subprocess.run(['mount','--bind',str(actual),str(slot)],check=True,capture_output=True)
 try:yield
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
ipa_modules=sorted((prefix/'usr/lib/libcamera/ipa').glob('*.so'));assert len(ipa_modules)==6;signatures=[]
with storage.sdk_candidate(),bind(prefix,SDK/'candidate420-r31'):
 for p in ipa_modules:
  q=subprocess.run(['chroot',str(SDK),'env','LD_LIBRARY_PATH=/candidate420-r31/usr/lib','/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify','/candidate420-r31/usr/lib/libcamera/ipa/'+p.name],capture_output=True)
  (P/(p.name+'-signature.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout;signatures.append(p.name)
old_prefix=source.parent/'camera391-package-prefix';ipa_equal={p.name:p.read_bytes()==(old_prefix/'usr/lib/libcamera/ipa'/p.name).read_bytes() for p in ipa_modules};assert all(ipa_equal.values()),'Inspect changed packaged IPA before reusing unchanged numerical evidence'
actual={n:hashlib.sha256((prefix/n).read_bytes()).hexdigest() for n in ['usr/lib/libcamera.so.0.7.2','usr/lib/libcamera-base.so.0.7.2','usr/lib/libcamera/ipa/ipa_camss_vfe.so','usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign','usr/libexec/libcamera/camss_ipa_proxy','usr/lib/gstreamer-1.0/libgstlibcamera.so','usr/libexec/libcamera/v4l2-compat.so','usr/bin/cam']}
(P/'installed-file-sha256.json').write_text(json.dumps(actual,indent=2)+'\n');(P/'runtime-records.json').write_text(json.dumps([r for r in records if r['runtime']],indent=2)+'\n')
report=dict(stage=420,packages=records,all_previous_feature_packages_preserved=True,runtime_packages=7,ipa_modules=6,all_ipa_signatures_verified_against_packaged_core=signatures,packaged_ipa_binary_identical_to_r30=ipa_equal,unchanged_ipa_mathematical_contract_reused_from_stage362=True,signed_forward_and_r30_r25_rollback_repositories=True,default_configuration_data_unchanged=True,private_factory_profiles_not_packaged=True,sdk_binds_unmounted=True,hardware_exercised=False,installed=False,passed=True)
(HERE/'package-artifact-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=420,packages=len(records),runtime_packages=7,ipa_modules=6,all_ipa_binaries_match_r30=True,packaged_core_sha256=actual['usr/lib/libcamera.so.0.7.2'],passed=True),indent=2))
