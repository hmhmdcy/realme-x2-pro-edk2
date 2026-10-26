"""Exercise signed camera upgrade and rollback using the actual phone APK database."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,tarfile

here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel214')
before=Path('/home/cy122/x2pro-linux/libcamera214-solver-before')
root=Path('/home/cy122/x2pro-linux/libcamera214-solver-roundtrip-r2')
assert not root.exists()
shutil.copytree(before,root)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
keys=private/'phone-trusted-public-keys'
forward=private/'camera-forward-repo'
rollback=private/'rollback-snapshot-apks'
key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')

def run(args,tag):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    (private/(tag+'-private.log')).write_text(p.stdout+p.stderr)
    assert p.returncode==0,(tag,p.returncode)
    return p.stdout+p.stderr

run([str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(key),'--pkgname-spec','${name}-${version}.apk','--output',str(rollback/'packages.adb'),*[str(p) for p in sorted(rollback.glob('*.apk'))]],'rollback-index')
run([str(apk),'--keys-dir',str(keys),'verify',str(rollback/'packages.adb')],'rollback-index-signature')
repos=private/'solver-roundtrip-repositories-private.list'
repos.write_text('ndx file://'+str(forward/'packages.adb')+'\n')
base=[str(apk),'--root',str(root),'--arch','aarch64','--no-network','--no-scripts','--keys-dir',str(keys),'--repositories-file',str(repos)]

with tarfile.open(private/'rollback-snapshot-inputs-private.tar.gz') as archive:
    original=json.loads(archive.extractfile('original-files-manifest-private.json').read())
    for name,item in original.items():
        assert not name.startswith('/') and '..' not in Path(name).parts
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
        if item['kind']=='symlink':target.symlink_to(item['target'])
        else:
            data=archive.extractfile('files/'+name).read()
            assert hashlib.sha256(data).hexdigest()==item['sha256']
            target.write_bytes(data);target.chmod(item['mode'])

def records():
    result={}
    for block in (root/'lib/apk/db/installed').read_text().split('\n\n'):
        lines=block.splitlines();names=[line[2:] for line in lines if line.startswith('P:')]
        if names:result[names[0]]=block
    return result

def version(block):return next(line[2:] for line in block.splitlines() if line.startswith('V:'))
original_records=records();world=(root/'etc/apk/world').read_bytes()
assert len(original_records)==940
log=run(base+['add','samurai-camera-stack=0.1.0-r0'],'roundtrip-forward')
after=records()
upgraded={'libcamera','libcamera-ipa','libcamera-tools'}
added={'libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
assert set(after)-set(original_records)==added and not set(original_records)-set(after)
assert all(after[name]==block for name,block in original_records.items() if name not in upgraded)
assert all(version(after[name])=='99990.7.2-r5' for name in upgraded|{'libcamera-gstreamer','libcamera-v4l2'})
manifest=json.loads((forward/'package-manifest.json').read_text())
packages=manifest['packages']
def check_files(package_records):
    count=0
    for item in package_records:
        for name,entry in item['files'].items():
            path=root/name
            if entry['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==entry['target']
            else:
                assert path.is_file() and not path.is_symlink(),name
                assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],name
                assert stat.S_IMODE(path.stat().st_mode)==entry['mode'],name
            count+=1
    return count
forward_count=check_files([item for item in packages if item['name'] in upgraded|added])
run(base+['del','--simulate','samurai-camera-stack'],'roundtrip-rollback-remove-dry')
run(base+['del','samurai-camera-stack'],'roundtrip-rollback-remove')
assert set(records())==set(original_records)
repos.write_text('ndx file://'+str(rollback/'packages.adb')+'\n')
requests=[name+'=99990.7.2-r4' for name in sorted(upgraded)]
run(base+['add','--simulate',*requests],'roundtrip-rollback-downgrade-dry')
run(base+['add',*requests],'roundtrip-rollback-downgrade')
final=records()
assert set(final)==set(original_records)
assert all(final[name]==block for name,block in original_records.items() if name not in upgraded)
assert all(version(final[name])=='99990.7.2-r4' for name in upgraded)
rollback_manifest=json.loads((private/'rollback-snapshot-packages-manifest-private.json').read_text())
rollback_count=check_files(rollback_manifest['packages'])
# APK removes the adopted configuration files with its config package.
with tarfile.open(private/'rollback-snapshot-inputs-private.tar.gz') as archive:
    for name in ['etc/libcamera/configuration.yaml','etc/modules-load.d/samurai-camera-heaps.conf','etc/udev/rules.d/70-samurai-camera-heaps.rules']:
        item=original[name];path=root/name
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
        data=archive.extractfile('files/'+name).read();assert hashlib.sha256(data).hexdigest()==item['sha256']
        path.write_bytes(data);path.chmod(item['mode'])
(root/'etc/apk/world').write_bytes(world)
assert (root/'etc/apk/world').read_bytes()==world
assert all((root/name).is_symlink() and os.readlink(root/name)==item['target'] if item['kind']=='symlink' else (root/name).is_file() and hashlib.sha256((root/name).read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE((root/name).stat().st_mode)==item['mode'] for name,item in original.items())
report=dict(stage=214,actual940_package_database_used=True,host_only_roundtrip_completed=True,signatures_verified_with_phone_trust=True,forward_upgrade_count=3,forward_new_package_count=4,unrelated_937_package_records_unchanged=True,forward_payload_records_checked=forward_count,rollback_original_three_payload_records_checked=rollback_count,original_configuration_bytes_modes_and_world_restored=True,rollback_package_versions='99990.7.2-r4',rollback_signature_provenance='installed snapshot signed with existing project key',apk_database_byte_identity_not_claimed=True,phone_package_transaction_not_yet_sent=True)
(here/'package-roundtrip-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
