from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');cache=json.loads((private/'rollback-apk-cache-private.json').read_text());original=json.loads((private/'phone-original-files-manifest-private.json').read_text());apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=private/'phone-trusted-public-keys';destination=private/'rollback-apks';destination.mkdir(mode=0o700,exist_ok=True);assert not any(destination.iterdir())
records=[]
for name in ['libcamera','libcamera-ipa']:
    matches=[Path(r['path']) for r in cache if r['file'].startswith(name+'-99990.7.2-r4.')];assert len(matches)==1;path=matches[0]
    p=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(path)],capture_output=True,timeout=20);(private/(name+'-rollback-phone-key-signature-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    compared=0
    with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:
        fields={}
        for line in archive.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:
                key,value=line.split(' = ',1);fields.setdefault(key,[]).append(value)
        assert fields['pkgname']==[name] and fields['pkgver']==['99990.7.2-r4']
        for member in archive.getmembers():
            relative=member.name.removeprefix('./')
            if member.isfile() and not relative.startswith('.'):
                assert original[relative]['kind']=='file' and original[relative]['sha256']==hashlib.sha256(archive.extractfile(member).read()).hexdigest() and original[relative]['mode']==member.mode,relative;compared+=1
            elif member.issym():assert original[relative]==dict(kind='symlink',target=member.linkname),relative;compared+=1
    copy=destination/(name+'-99990.7.2-r4.apk');shutil.copyfile(path,copy);records.append(dict(name=name,version='99990.7.2-r4',all_cached_payloads_match_current_device_backup=True,compared_file_records=compared,signature_verified=True))
report=dict(stage=214,rollback_main_and_ipa_original_signed_apks_verified=True,original_installed_payloads_and_modes_match=True,rollback_tools_apk_still_needed=True,packages=records,phone_not_modified=True);(here/'rollback-cache-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
