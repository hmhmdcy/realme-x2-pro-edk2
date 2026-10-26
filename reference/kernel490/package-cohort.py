"""Sign r34/r29 cached payloads and preserve exact r33/r28 rollback; no SDK."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,struct,subprocess,tarfile,time
import storage
from importlib.util import spec_from_file_location,module_from_spec
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel490')
OLD=PRIVATE.parent/'kernel475';CORE=PRIVATE.parent/'kernel489/build-r1/libcamera.so.0.7.2'
CORE_SHA='b345af8b1430718b8fbcbbfde95916d66312bf0fc0e1b237edfb177332818bdd'
CORE_PATH='usr/lib/libcamera.so.0.7.2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inventory(root):
    rows={}
    for path in sorted(root.rglob('*')):
        name=path.relative_to(root).as_posix()
        if path.is_symlink():rows[name]={'symlink':os.readlink(path)}
        elif path.is_file():rows[name]=dict(sha256=sha(path),bytes=path.stat().st_size,mode=path.stat().st_mode&0o7777)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',required=True,choices=['r1','r2','r3'])
    parser.add_argument('--build-time',type=int,default=int(time.time()))
    args=parser.parse_args();workspace=storage.workspace();volume=workspace.parent
    measured=json.loads((PRIVATE/'input-measurement-private.json').read_text());assert measured['passed']
    assert shutil.disk_usage(volume).free>2*1024**3+2*measured['total_regular_bytes']+128*1024**2
    baseline=HERE.parent/'kernel475';candidate=json.loads((baseline/'candidate-state.json').read_text())
    report_path=baseline/'package-r1-validation.json';assert sha(report_path)==candidate['public_files_sha256'][report_path.name]
    old_report=json.loads(report_path.read_text());old_state_path=OLD/'package-state-r1-private.json'
    assert sha(old_state_path)==measured['cached_package_state_sha256'];old_state=json.loads(old_state_path.read_text())
    reports489={name:json.loads((HERE.parent/'kernel489'/name).read_text()) for name in ['source-state.json','build-validation.json','sdk-validation.json']}
    assert all(row['passed'] for row in reports489.values()) and sha(CORE)==CORE_SHA and CORE.stat().st_size==51262920
    work=workspace/args.attempt;repo=PRIVATE/('repository-'+args.attempt)
    assert not work.exists() and not repo.exists(),'Preserve all prior attempts'
    work.mkdir(parents=True);(repo/'forward').mkdir(parents=True);(repo/'rollback').mkdir()
    apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
    keys=OLD/'isolated-union-public-keys'
    signing=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
    assert apk.is_file() and keys.is_dir() and signing.is_file()
    commands=[]
    def run(arguments,label):
        result=subprocess.run(arguments,capture_output=True,timeout=120)
        path=PRIVATE/(args.attempt+'-'+label+'-private.log');assert not path.exists();path.write_bytes(result.stdout+result.stderr)
        commands.append(dict(label=label,exit_code=result.returncode,log_sha256=sha(path)))
        if result.returncode:
            (PRIVATE/(args.attempt+'-failure-private.json')).write_text(json.dumps(dict(failed=True,commands=commands),indent=2)+'\n')
            raise RuntimeError(label+' failed; inspect retained private log, do not replay attempt')
        return result
    prefix=[str(apk),'--keys-dir',str(keys)]
    old_repo=OLD/'repository-r1/forward'
    manifest_path=OLD/'cohort-r2-manifest-private.json';manifest=json.loads(manifest_path.read_text())
    assert sha(manifest_path)==json.loads((baseline/'private-archive-r2-validation.json').read_text())['revised_manifest_sha256']
    for path in sorted(old_repo.iterdir()):
        assert path.is_file() and sha(path)==manifest['files_sha256']['forward/repository/'+path.name]
        shutil.copyfile(path,repo/'rollback'/path.name)
    assert len(list((repo/'rollback').glob('*.apk')))==7
    run(prefix+['verify']+[str(p) for p in sorted((repo/'rollback').iterdir())],'verify-rollback-eight')
    by_name={row['name']:row['after_files'] for row in old_state['inventories']}
    versions={row['name']:'0.1.0-r29' if row['name'].startswith('samurai-camera-') else '99990.7.2-r34' for row in old_report['packages']}
    remap=lambda text:text.replace('99990.7.2-r33','99990.7.2-r34').replace('0.1.0-r28','0.1.0-r29')
    records=[];inventories=[];roots={};combined={};changed=[]
    for record in old_report['packages']:
        name=record['name'];original=old_repo/record['file'];assert sha(original)==record['sha256']
        source=Path(old_state['roots'][name]);before=inventory(source);assert before==by_name[name]
        target=work/'payloads'/name;shutil.copytree(source,target,symlinks=True)
        if name=='libcamera':
            assert CORE_PATH in before;shutil.copyfile(CORE,target/CORE_PATH)
            (target/CORE_PATH).chmod(before[CORE_PATH]['mode'])
        after=inventory(target);assert before.keys()==after.keys()
        delta=[path for path in before if before[path]!=after[path]]
        assert delta==([CORE_PATH] if name=='libcamera' else []),(name,delta)
        changed.extend(delta)
        metadata_package=PRIVATE.parent/'kernel440/runtime-repository-r2/forward'/record['inherited_from']
        assert sha(metadata_package)==record['source_package_sha256']
        with tarfile.open(metadata_package,'r:gz',ignore_zeros=True) as archive:
            metadata={}
            for line in archive.extractfile('.PKGINFO').read().decode().splitlines():
                if ' = ' in line:
                    key,value=line.split(' = ',1);metadata.setdefault(key,[]).append(value)
        dependencies=[remap(value) for value in record['dependencies']]
        current_provides=[value.replace('99990.7.2-r32','99990.7.2-r33').replace('0.1.0-r27','0.1.0-r28') for value in metadata.get('provides',[])]
        provides=[remap(value) for value in current_provides]
        info=dict(name=name,version=versions[name],arch=metadata['arch'][0],description=metadata['pkgdesc'][0],
            license=metadata['license'][0],origin=metadata['origin'][0],url=metadata['url'][0],
            **{'build-time':str(args.build_time),'depends':' '.join(dependencies)})
        if provides:info['provides']=' '.join(provides)
        if metadata.get('maintainer'):info['maintainer']=metadata['maintainer'][0]
        output=repo/'forward'/(name+'-'+versions[name]+'.apk')
        arguments=prefix+['mkpkg','--compression','deflate:9','--sign-key',str(signing),'--files',str(target),'--output',str(output)]
        for key,value in info.items():
            if value:arguments.extend(['--info',key+':'+value])
        run(arguments,'mkpkg-'+name)
        roots[name]=str(target);inventories.append(dict(name=name,before_files=before,after_files=after))
        for path,row in after.items():assert path not in combined or combined[path]==row;combined[path]=row
        records.append(dict(name=name,version=versions[name],arch=metadata['arch'][0],file=output.name,bytes=output.stat().st_size,
            sha256=sha(output),dependencies=dependencies,provides=provides,rollback_file=record['file'],rollback_sha256=record['sha256'],
            metadata_r32_file=record['inherited_from'],metadata_r32_sha256=record['source_package_sha256'],changed_payload=delta))
    assert changed==[CORE_PATH] and len(combined)==57
    forward=repo/'forward'
    run(prefix+['mkndx','--compression','deflate:9','--sign-key',str(signing),'--pkgname-spec','${name}-${version}.apk',
        '--description','CAMSS490 r34 r29','--output',str(forward/'packages.adb')]+[str(p) for p in sorted(forward.glob('*.apk'))],'index-forward')
    run(prefix+['verify']+[str(p) for p in sorted(forward.iterdir())],'verify-forward-eight')
    extracted=work/'extracted-r34';extracted.mkdir()
    run(prefix+['extract','--destination',str(extracted)]+[str(p) for p in sorted(forward.glob('*.apk'))],'extract-signed-payloads')
    assert inventory(extracted)==combined,'Actual signed APK payload differs from prepared roots'
    for path in extracted.rglob('*'):
        values=path.lstat();assert values.st_uid==values.st_gid==0
        if path.is_dir() and not path.is_symlink():assert values.st_mode&0o7777==0o755,str(path)
    raw=(extracted/CORE_PATH).read_bytes();assert hashlib.sha256(raw).hexdigest()==CORE_SHA
    shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    dynamic=next(row for row in sections if names[row[0]:].split(bytes([0]))[0]==b'.dynamic')
    tags=[]
    for tag,value in struct.iter_unpack('<qQ',raw[dynamic[4]:dynamic[4]+dynamic[5]]):
        if tag==0:break
        tags.append(tag)
    assert not {15,29}&set(tags)
    for record in old_report['packages']:assert sha(old_repo/record['file'])==record['sha256']
    assert all(inventory(Path(old_state['roots'][name]))==by_name[name] for name in old_state['roots'])
    free=shutil.disk_usage(volume).free;assert free>2*1024**3
    private_state=dict(stage=490,attempt=args.attempt,build_time=args.build_time,work=str(work),repository=str(repo),roots=roots,inventories=inventories,
        packages=records,index_sha256={kind:sha(repo/kind/'packages.adb') for kind in ['forward','rollback']},
        runtime_inputs={CORE_PATH:dict(path=str(CORE),sha256=CORE_SHA)},commands=commands,
        old_package_state_sha256=sha(old_state_path),old_package_report_sha256=sha(report_path),
        input489_sha256={name:sha(HERE.parent/'kernel489'/name) for name in reports489})
    state_path=PRIVATE/('package-state-'+args.attempt+'-private.json');state_path.write_text(json.dumps(private_state,indent=2)+'\n')
    report=dict(stage=490,attempt=args.attempt,passed=True,framework_version='99990.7.2-r34',configuration_version='0.1.0-r29',
        rollback_versions={row['name']:row['version'] for row in old_report['packages']},packages=records,
        payload_entries=57,unchanged_payload_entries=56,changed_payload_paths=changed,actual_signed_payload_extraction_byte_exact=True,
        signed_forward_and_exact_rollback_repository_verified=True,index_sha256=private_state['index_sha256'],
        core_sha256=CORE_SHA,core_bytes=len(raw),core_rpath_and_runpath_absent=True,other_ELF_bytes_preserved=True,
        cached_binary_repack_only=True,compiled=False,strip_performed=False,ipa_resigned=False,
        private_coefficients_modules_profiles_added=False,apk_database_transaction_performed=False,dependency_solver_executed=False,
        loader_or_device_execution_performed=False,no_sdk_access=True,no_ssh=True,no_usb=True,no_pm=True,
        source_roots_and_original_r33_packages_preserved=True,free_after_bytes=free,package_state_sha256=sha(state_path),
        command_results=[dict(label=row['label'],exit_code=row['exit_code']) for row in commands])
    destination=HERE/('package-'+args.attempt+'-validation.json');assert not destination.exists();destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=490,passed=True,attempt=args.attempt,signed_forward_packages=7,exact_rollback_packages=7,changed_payloads=1,free_after_bytes=free)))


if __name__=='__main__':main()
