from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
code=r'''
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
files=[]
for folder in sorted(root.glob('k213-*')):
    if folder.is_dir() and not folder.is_symlink() and folder.name not in ['k213-libcamera-sdk','k213-libcamera-build']:
        files.extend(p for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink())
build=root/'k213-libcamera-build'
files.extend(p for p in sorted(build.iterdir()) if p.is_file() and p.suffix in ['.log','.json','.cpp','.patch'])
files.extend(build/'source/libcamera-v0.7.2'/name for name in ['src/ipa/libipa/camera_sensor_helper.cpp','src/libcamera/sensor/camera_sensor_properties.cpp','src/libcamera/software_isp/debayer_cpu.cpp','src/libcamera/software_isp/debayer_cpu.h'])
for variant in ['helper','lut']:
    prefix=Path('/run/samurai-camera213-'+variant)
    files.extend(prefix/name for name in ['usr/bin/cam','usr/lib/libcamera.so.0.7.2','usr/lib/libcamera-base.so.0.7.2','usr/lib/libcamera/ipa/ipa_soft_simple.so','usr/lib/libcamera/ipa/ipa_soft_simple.so.sign','usr/libexec/libcamera/soft_ipa_proxy'])
for name in ['raw-dark-sync-probe','csid-known-input-sync-probe']:
    files.append(Path('/run/samurai-camera213-'+name))
assert len(files)==len(set(files)) and not any('ipa-priv-key' in p.name or p.suffix=='.pem' or 'k213-libcamera-sdk' in p.parts for p in files)
destination=Path('/tmp/k213-final-evidence-private.tar.gz');assert not destination.exists();records={}
with tarfile.open(destination,'w:gz') as archive:
    for path in files:
        data=path.read_bytes();name=str(path).removeprefix('/');info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
        archive.addfile(info,io.BytesIO(data));records[name]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(path=str(destination),size=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=records)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);record=json.loads(p.stdout);(host.PRIVATE/'final-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as destination:
    for offset in range(0,record['size'],1048576):
        p=host.ssh('dd if='+record['path']+' bs=1048576 skip='+str(offset//1048576)+' count=1',timeout=50);assert len(p.stdout)==min(1048576,record['size']-offset);destination.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=213,private_archive_all_members_verified=True,archived_regular_files=len(members),raw_scene_images_and_logs_kept_private=True,isolated_sdk_and_ipa_private_key_excluded=True,candidate_binaries_and_build_logs_preserved=True,transfer_in_one_mib_chunks=True,clean_current_boot=True,initial_fetch_configure_link_probe_and_sensor_pattern_failures_preserved=True)
(here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
