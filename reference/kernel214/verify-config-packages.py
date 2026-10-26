from pathlib import Path
import hashlib,json,subprocess,tarfile
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
assert json.loads((here/'config-package-build-validation.json').read_text())['all_project_signatures_verified']
records=[]
expected={'etc/libcamera/configuration.yaml':repo/'linux-port/camera/configuration.yaml','etc/modules-load.d/samurai-camera-heaps.conf':repo/'linux-port/camera/samurai-camera-heaps.conf','etc/udev/rules.d/70-samurai-camera-heaps.rules':repo/'linux-port/camera/70-samurai-camera-heaps.rules'}
for path in sorted((root/'packages-config').rglob('*.apk')):
    p=subprocess.run([str(apk),'--keys-dir',str(root/'etc/apk/keys'),'verify',str(path)],capture_output=True);(private/(path.name+'-host-verify-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    assert path.read_bytes().startswith(b'\x1f\x8b')
    with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:
        fields={}
        for line in archive.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:
                key,value=line.split(' = ',1);fields.setdefault(key,[]).append(value)
        assert fields['arch']==['noarch'] and fields['pkgver']==['0.1.0-r0']
        files={m.name.removeprefix('./'):dict(sha256=hashlib.sha256(archive.extractfile(m).read()).hexdigest(),mode=m.mode) for m in archive.getmembers() if m.isfile() and not m.name.startswith('.')}
        assert not any(m.isfile() and m.name.startswith(('.pre-','.post-')) for m in archive.getmembers())
        if fields['pkgname']==['samurai-camera-config']:
            assert set(files)==set(expected)
            assert all(files[name]==dict(sha256=hashlib.sha256(src.read_bytes()).hexdigest(),mode=0o644) for name,src in expected.items())
            dirs={m.name.removeprefix('./').rstrip('/'):m.mode for m in archive.getmembers() if m.isdir()};assert dirs['etc/libcamera']==0o755
        else:assert fields['pkgname']==['samurai-camera-stack'] and not files
        records.append(dict(name=fields['pkgname'][0],version=fields['pkgver'][0],file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,files=files,dependencies=fields.get('depend',[])))
report=dict(stage=214,signature_verification_with_host_apk_passed=True,config_payloads_exact_and_modes_verified=True,no_runtime_scripts=True,packages=records,phone_not_modified=True)
(here/'config-package-payload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
