from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-rollback-build');assert not root.exists();root.mkdir(mode=0o700)
out=private/'rollback-snapshot-apks';assert not out.exists();out.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa');keys=private/'phone-trusted-public-keys';epoch=1792022400
proof=json.loads((here/'rollback-snapshot-inputs-validation.json').read_text());assert proof['all_snapshot_file_hashes_verified'] and proof['current_same_boot_and_unchanged_database_verified']
records=[]
with tarfile.open(private/'rollback-snapshot-inputs-private.tar.gz') as archive:
    original=json.loads(archive.extractfile('original-files-manifest-private.json').read());packages=json.loads(archive.extractfile('metadata-private.json').read())
    for name,item in packages.items():
        fields=item['fields'];assert fields['P']==name and fields['V']=='99990.7.2-r4' and fields['A']=='aarch64';payload=root/name;payload.mkdir(mode=0o755);manifest={}
        for relative in item['files']:
            assert relative.startswith('usr/') and '..' not in Path(relative).parts;record=original[relative];target=payload/relative;target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            if record['kind']=='symlink':target.symlink_to(record['target']);manifest[relative]=record
            else:
                assert record['kind']=='file';data=archive.extractfile('files/'+relative).read();assert hashlib.sha256(data).hexdigest()==record['sha256'];target.write_bytes(data);target.chmod(record['mode']);manifest[relative]=record
        for path in [payload,*payload.rglob('*')]:
            if path.is_dir():path.chmod(0o755)
            if not path.is_symlink():os.chown(path,0,0)
            os.utime(path,(epoch,epoch),follow_symlinks=False)
        metadata=dict(name=name,version=fields['V'],arch=fields['A'],description=fields['T']+' (installed r4 rollback snapshot)',license=fields['L'],url=fields['U'],origin=fields.get('o','libcamera'),maintainer='Realme X2 Pro Linux port - installed snapshot',depends=fields.get('D',''),provides=fields.get('p',''),**{'build-time':str(epoch)})
        if fields.get('i'):metadata['install-if']=fields['i']
        if fields.get('r'):metadata['replaces']=fields['r']
        target=out/(name+'-'+fields['V']+'.apk');command=[str(apk),'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',str(payload),'--sign-key',str(key),'--output',str(target)]
        for k,v in sorted(metadata.items()):
            if v:command.extend(['--info',k+':'+v])
        p=subprocess.run(command,capture_output=True,timeout=60);(private/(name+'-snapshot-mkpkg-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
        p=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(target)],capture_output=True,timeout=20);(private/(name+'-snapshot-signature-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
        records.append(dict(name=name,version=fields['V'],file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,metadata=metadata,files=manifest))
assert len(records)==3
(private/'rollback-snapshot-packages-manifest-private.json').write_text(json.dumps(dict(source='actual214 installed-r4 backup',packages=records),indent=2)+'\n')
report=dict(stage=214,installed_r4_rollback_snapshot_packages_built=True,package_count=3,all_original_payload_bytes_symlinks_and_modes_preserved=True,metadata_dependencies_and_provides_preserved=True,versions_preserved='99990.7.2-r4',signed_with_existing_project_key_trusted_by_current_phone=True,signature_verification_passed=True,cached_archives_with_unavailable_signing_key_not_used=True,snapshot_provenance_explicit_not_claimed_as_upstream_signature=True,private_snapshot_packages_not_published=True,no_device_mutation=True)
(here/'rollback-snapshot-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
