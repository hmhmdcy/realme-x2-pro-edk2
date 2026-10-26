"""Stage selected signed APKs, the complete runtime, rollback and finite probes."""
from pathlib import Path
import hashlib,host,io,json,os,shlex,subprocess,tarfile

here=Path(__file__).resolve().parent;private=host.PRIVATE
assert json.loads((here/'package-roundtrip-validation.json').read_text())['host_only_roundtrip_completed']
full=private/'camera-forward-repo';manifest=json.loads((full/'package-manifest.json').read_text())
names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
selected=[p for p in manifest['packages'] if p['name'] in names];assert len(selected)==7
subset=private/'camera-selected-repo';assert not subset.exists();subset.mkdir(mode=0o700)
import shutil
for item in selected:shutil.copyfile(full/item['file'],subset/item['file'])
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
p=subprocess.run([str(apk),'--keys-dir',str(private/'phone-trusted-public-keys'),'mkndx','--compression','deflate:9','--sign-key',str(key),'--pkgname-spec','${name}-${version}.apk','--output',str(subset/'packages.adb'),*[str(subset/item['file']) for item in selected]],capture_output=True,timeout=60)
(private/'selected-index-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
rollback=json.loads((private/'rollback-snapshot-packages-manifest-private.json').read_text())
probes=json.loads((here/'probe-build-validation.json').read_text())['probes']
bundle=private/'full-camera-candidate-bundle-private.tar.gz';assert not bundle.exists();members={}
qa=Path('/home/cy122/x2pro-linux/libcamera214-qa-prefix')
with tarfile.open(bundle,'w:gz') as archive:
    def add(name,data,mode=0o600):
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;archive.addfile(info,io.BytesIO(data));members[name]=dict(kind='file',sha256=hashlib.sha256(data).hexdigest(),mode=mode)
    for directory,records in [('forward',selected),('rollback',rollback['packages'])]:
        source=subset if directory=='forward' else private/'rollback-snapshot-apks'
        for item in records:
            data=(source/item['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256'];add(directory+'/'+item['file'],data)
        add(directory+'/packages.adb',(source/'packages.adb').read_bytes())
    for item in selected:
        for name,record in item['files'].items():
            if name.startswith('etc/'):continue
            path=qa/name;member='candidate/'+name
            if record['kind']=='symlink':
                assert path.is_symlink() and os.readlink(path)==record['target'];info=tarfile.TarInfo(member);info.type=tarfile.SYMTYPE;info.linkname=record['target'];info.mode=0o777;archive.addfile(info);members[member]=record
            else:
                data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==record['sha256'];add(member,data,record['mode'])
    for item in probes:
        data=(private/'probes'/item['name']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256'];add('probes/'+item['name'],data,0o755)
    add('forward-manifest.json',json.dumps(dict(packages=selected),indent=2).encode())
    add('rollback-manifest-private.json',json.dumps(rollback,indent=2).encode())
    add('bundle-manifest-private.json',json.dumps(members,indent=2).encode())
record=dict(bytes=bundle.stat().st_size,sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),members=members)
(private/'candidate-bundle-metadata-private.json').write_text(json.dumps(record,indent=2)+'\n')
start=r'''
from pathlib import Path
import json
base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(base/'apk-installed-before-private.txt').read_bytes()
out=Path('/var/lib/samurai/k214-package-candidates');out.mkdir(mode=0o700)
p=out/'bundle-private.tar.gz';p.touch(mode=0o600,exist_ok=False)
print(json.dumps(dict(ready=True)))
'''
p=host.ssh('python3 -',input=start.encode(),timeout=30);assert json.loads(p.stdout)['ready']
data=bundle.read_bytes()
for offset in range(0,len(data),65536):
    chunk=data[offset:offset+65536]
    code="from pathlib import Path;import sys; p=Path('/var/lib/samurai/k214-package-candidates/bundle-private.tar.gz');assert p.stat().st_size=="+str(offset)+"; data=sys.stdin.buffer.read();assert len(data)=="+str(len(chunk))+";p.open('ab').write(data)"
    p=host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
    (private/'candidate-bundle-transfer-offset-private.txt').write_text(str(offset+len(chunk)))
    if offset//65536%20==0:print(json.dumps(dict(uploaded_bytes=offset+len(chunk),total_bytes=len(data))),flush=True)
finish=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k214-package-candidates');bundle=out/'bundle-private.tar.gz'
assert bundle.stat().st_size==EXPECTED_SIZE and hashlib.sha256(bundle.read_bytes()).hexdigest()==EXPECTED_HASH
prefix=Path('/run/samurai-camera214-full');prefix.mkdir(mode=0o755)
with tarfile.open(bundle) as archive:
    manifest=json.loads(archive.extractfile('bundle-manifest-private.json').read())
    assert {m.name for m in archive.getmembers()}==set(manifest)|{'bundle-manifest-private.json'}
    for member in archive.getmembers():
        name=member.name;assert not name.startswith('/') and '..' not in Path(name).parts
        target=prefix/name[len('candidate/'):] if name.startswith('candidate/') else out/name
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o755 if name.startswith(('candidate/','probes/')) else 0o700)
        if member.issym():
            assert '..' not in Path(member.linkname).parts and manifest[name]['target']==member.linkname
            target.symlink_to(member.linkname)
        else:
            assert member.isfile();data=archive.extractfile(member).read()
            if name in manifest:assert hashlib.sha256(data).hexdigest()==manifest[name]['sha256']
            target.write_bytes(data);target.chmod(member.mode)
for directory in [prefix,*prefix.rglob('*')]:
    if directory.is_dir() and not directory.is_symlink():directory.chmod(0o755)
for directory in ['forward','rollback']:
    for path in sorted((out/directory).iterdir()):
        p=subprocess.run(['apk','verify',str(path)],capture_output=True,timeout=30)
        (out/(path.name+'.signature-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert Path('/lib/apk/db/installed').read_bytes()==(base/'apk-installed-before-private.txt').read_bytes()
report=dict(stage=214,seven_forward_apks_and_three_rollback_apks_staged=True,both_repository_indexes_verified_with_existing_phone_trust=True,all_package_signatures_verified_on_phone=True,isolated_full_candidate_runtime_staged=True,finite_no_runpath_probes_staged=True,archive_and_all_member_hashes_verified=True,private_signing_keys_not_uploaded=True,system_camera_packages_unchanged=True)
(out/'staging-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('EXPECTED_SIZE',str(record['bytes'])).replace('EXPECTED_HASH',repr(record['sha256']))
p=host.ssh('python3 -',input=finish.encode(),timeout=100);(private/'candidate-staging-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'full-candidate-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
