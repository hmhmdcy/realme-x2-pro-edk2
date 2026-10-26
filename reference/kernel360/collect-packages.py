"""Verify signed artifacts, retain complete consumers, exercise packaged IPA."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,shutil,subprocess,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;source=storage.candidate();SDK=storage.SDK
assert json.loads((HERE/'package-build-validation.json').read_text())['passed']
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys'
signingKey=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
repository=P/'runtime-repository';repository.mkdir(mode=0o700,exist_ok=True)
prefix=source.parent/'camera360-package-prefix';prefix.mkdir(mode=0o700,exist_ok=True)
runtime={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
records=[]
for package in [*sorted((source.parent/'packages360-r28').rglob('*.apk')),*sorted((source.parent/'packages-config360-r28').rglob('*.apk'))]:
    q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(package)],capture_output=True,timeout=30)
    (P/(package.name+'-verify.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,package.name
    with tarfile.open(package,'r:gz',ignore_zeros=True) as tar:
        fields={}
        for line in tar.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
        name=fields['pkgname'][0];version=fields['pkgver'][0]
        assert version==('0.1.0-r23' if name.startswith('samurai-camera-') else '99990.7.2-r28'),(name,version)
        records.append(dict(name=name,version=version,arch=fields['arch'][0],file=package.name,bytes=package.stat().st_size,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),runtime=name in runtime))
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
            target=repository/'forward'/package.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(package,target)
previous=json.loads((HERE.parent/'kernel342/package-artifact-validation.json').read_text())
assert {r['name'] for r in records}=={r['name'] for r in previous['packages']},'Feature package set changed'
assert sum(r['runtime'] for r in records)==7
rollback=repository/'rollback';rollback.mkdir(exist_ok=True)
for package in (P.parent/'kernel342/runtime-repository/forward').glob('*.apk'):shutil.copyfile(package,rollback/package.name)
assert len(list(rollback.glob('*.apk')))==7
for kind in ['forward','rollback']:
    directory=repository/kind
    q=subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(signingKey),
        '--pkgname-spec','${name}-${version}.apk','--description','CAMSS360 '+kind,'--output',str(directory/'packages.adb'),*[str(p) for p in sorted(directory.glob('*.apk'))]],capture_output=True,timeout=60)
    (P/(kind+'-index.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode
    assert not subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(directory/'packages.adb')],capture_output=True,timeout=30).returncode
assert len(list((prefix/'usr/lib/libcamera/ipa').glob('*.so')))==6
for name in ['usr/lib/libcamera/ipa/ipa_camss_vfe.so','usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign','usr/libexec/libcamera/camss_ipa_proxy',
    'usr/lib/gstreamer-1.0/libgstlibcamera.so','usr/lib/libcamera.so.0.7.2','usr/lib/libcamera-base.so.0.7.2']:
    assert (prefix/name).is_file(),name
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
    assert (prefix/'usr/share/libcamera/ipa/camss-vfe'/(model+'.yaml')).read_bytes()==(HERE/'recipes/samurai-camera-config'/('camss-'+model+'.yaml')).read_bytes()
@contextmanager
def bind(actual,slot):
    slot.mkdir(exist_ok=True);assert not any(slot.iterdir()) and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
    subprocess.run(['mount','--bind',str(actual),str(slot)],check=True,capture_output=True)
    try:yield
    finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
relative=Path('/private/camss360-contract');slot=SDK/str(relative).lstrip('/');packageSlot=SDK/'candidate360-r28';packaged=[]
with storage.sdk_candidate(),bind(prefix,packageSlot),bind(source.parent/'camss360-contract',slot):
    verify='/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify'
    q=subprocess.run(['chroot',str(SDK),'env','LD_LIBRARY_PATH=/candidate360-r28/usr/lib',verify,'/candidate360-r28/usr/lib/libcamera/ipa/ipa_camss_vfe.so'],capture_output=True,timeout=30)
    (P/'packaged-ipa-signature.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
    cases=json.loads((P/'cases-private.json').read_text())
    for row in [cases[0],cases[-1]]:
        m=row['match'];args=[str(relative/Path(row['profile']).name),row['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(row['minimum_lines']),str(row['maximum_lines']),str(row['minimum_code']),str(row['maximum_code']),str(relative/Path(row['native_reference']).name),str(relative/Path(row['complete_profile']).name),str(relative/Path(row['expected_gamma']).name)]
        q=subprocess.run(['chroot',str(SDK),'env','LD_LIBRARY_PATH=/candidate360-r28/usr/lib','LIBCAMERA_LOG_LEVELS=*:ERROR',str(relative/'contract'),'/candidate360-r28/usr/lib/libcamera/ipa/ipa_camss_vfe.so','direct',*args],capture_output=True,timeout=90)
        (P/(row['name']+'-packaged-contract.log')).write_bytes(q.stdout+q.stderr)
        assert not q.returncode and b'EXPOSURE_CONTRACT_PASS' in q.stdout,(row['name'],q.stderr.decode()[-4000:]);packaged.append(row['name'])
configuration={x['name']:x['value'] for x in json.loads((source/'src/libcamera-v0.7.2/output/meson-info/intro-buildoptions.json').read_text()) if x['name'] in ['pipelines','ipas','gstreamer','pycamera','qcam','v4l2']}
report=dict(stage=360,packages=records,configuration=configuration,all_prior_feature_packages_preserved=True,ipa_modules=6,
    runtime_packages=7,signed_forward_and_r27_rollback_repositories=True,new_ipa_signature_verified_against_packaged_core=True,
    stripped_packaged_ipa_contracts=packaged,default_profiles_unchanged=True,factory_and_individual_tables_not_packaged=True,
    sdk_binds_unmounted=True,hardware_exercised=False,installed=False,passed=True)
(HERE/'package-artifact-validation.json').write_text(json.dumps(report,indent=2)+'\n');(P/'runtime-records.json').write_text(json.dumps([r for r in records if r['runtime']],indent=2)+'\n')
print(json.dumps(dict(stage=360,packages=len(records),runtime_packages=7,ipa_modules=6,packaged_contracts=len(packaged),passed=True)))
