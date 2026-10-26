from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,tarfile
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel275');root=Path('/home/cy122/x2pro-linux/libcamera214-root');apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=private.parent/'kernel214/phone-trusted-public-keys';key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
assert json.loads((here/'r22-package-build-validation.json').read_text())['framework_and_config_packages_built']
features=json.loads((here/'r22-full-feature-configuration-validation.json').read_text());assert features['all_required_feature_targets_found'] and features['gpu_isp_still_compiled'] and features['ipa_signing_public_key_enabled']
out=private/'camera-forward-repo-r22';assert not out.exists();out.mkdir(mode=0o700);prefix=Path('/home/cy122/x2pro-linux/libcamera275-r22-qa-prefix');assert not prefix.exists();prefix.mkdir(mode=0o700)
sources=[*sorted((root/'packages275-r22').rglob('*.apk')),*sorted((root/'packages-config275-r22').rglob('*.apk'))];assert len(sources)==13
secrets=[key.read_bytes(),Path('/home/cy122/x2pro-linux/libcamera214-signing-private/ipa.rsa.pem').read_bytes()]
records=[];owners={};elf_count=0
for source in sources:
    target=out/source.name;shutil.copyfile(source,target)
    p=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(target)],capture_output=True,timeout=20);(private/(target.name+'-verify-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    assert target.read_bytes().startswith(b'\x1f\x8b')
    files={};directories={}
    with tarfile.open(target,'r:gz',ignore_zeros=True) as archive:
        fields={}
        for line in archive.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:
                k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
        name=fields['pkgname'][0];version=fields['pkgver'][0];assert version==('0.1.0-r17' if name.startswith('samurai-camera-') else '99990.7.2-r22') and fields['arch'][0] in ['aarch64','noarch']
        assert not any(m.name.startswith(('.pre-','.post-','.trigger')) for m in archive.getmembers())
        for member in archive.getmembers():
            relative=member.name.removeprefix('./').rstrip('/')
            if not relative or relative.startswith('.'):continue
            assert not relative.startswith('/') and '..' not in Path(relative).parts and relative.startswith(('usr','etc'))
            assert not relative.endswith('.pem') and 'ipa-priv-key' not in relative
            dest=prefix/relative
            if member.isdir():dest.mkdir(parents=True,exist_ok=True,mode=0o755);dest.chmod(member.mode);directories[relative]=member.mode;continue
            assert relative not in owners,relative;owners[relative]=name;dest.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            if member.issym():
                assert '..' not in Path(member.linkname).parts;dest.symlink_to(member.linkname);files[relative]=dict(kind='symlink',target=member.linkname)
            else:
                assert member.isfile(),relative;data=archive.extractfile(member).read();assert not any(secret in data for secret in secrets)
                if data.startswith(b'\x7fELF'):
                    assert data[5]==1 and int.from_bytes(data[18:20],'little')==183,relative;elf_count+=1
                dest.write_bytes(data);dest.chmod(member.mode);files[relative]=dict(kind='file',sha256=hashlib.sha256(data).hexdigest(),mode=member.mode)
    records.append(dict(name=name,version=version,arch=fields['arch'][0],file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),dependencies=fields.get('depend',[]),provides=fields.get('provides',[]),files=files,directories=directories))
required={'libcamera','libcamera-ipa','libcamera-tools','libcamera-dev','libcamera-gstreamer','libcamera-v4l2','libcamera-raspberrypi','qcam','py3-libcamera','py3-libcamera-pyc','libcamera-dbg','samurai-camera-config','samurai-camera-stack'};assert {r['name'] for r in records}==required
ipa=[name for name in owners if name.startswith('usr/lib/libcamera/ipa/') and name.endswith('.so')];assert len(ipa)==5
for name in ipa:assert name+'.sign' in owners
assert (prefix/'etc/libcamera/configuration.yaml').read_bytes()==(root/'work/samurai-camera-config275-r22/configuration.yaml').read_bytes()
assert stat.S_IMODE((prefix/'etc/libcamera').stat().st_mode)==0o755
manifest=dict(stage=275,source_date_epoch=1792022400,all_original_feature_packages_present=True,packages=records)
(out/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command=[str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(key),'--pkgname-spec','${name}-${version}.apk','--description','Realme X2 Pro camera224 full framework and device configuration','--output',str(out/'packages.adb'),*[str(p) for p in sorted(out.glob('*.apk'))]]
p=subprocess.run(command,capture_output=True,timeout=60);(private/'forward-repository-index-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
p=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(out/'packages.adb')],capture_output=True,timeout=20);(private/'forward-index-verify-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
(private/'forward-artifact-locations-private.json').write_text(json.dumps(dict(repository=str(out),qa_prefix=str(prefix)),indent=2)+'\n')
report=dict(stage=275,complete_forward_package_count=len(records),all_signatures_verified_with_current_phone_trust=True,all_original_feature_subpackages_present=True,five_ipa_modules_and_signatures_present=True,all_elf_files_aarch64=True,elf_file_count=elf_count,private_key_material_and_key_files_absent_from_payloads=True,no_runtime_scripts_in_camera_packages=True,payload_file_ownership_no_conflicts=True,cpu_config_directory_0755_verified=True,signed_local_repository_index_verified=True,phone_not_modified=True)
(here/'r22-forward-package-artifact-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
