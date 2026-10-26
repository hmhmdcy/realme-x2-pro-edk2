from pathlib import Path
import hashlib,json,tarfile,host,sys
here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k211-reboot-tools'
from_crtc='--from-crtc' in sys.argv
for name in (['disable-crtc-after-warning.py','finish-quiesce-crtc-after-warning.sh'] if from_crtc else ['check-quiesce-recovery.py','continue-quiesce-after-warning.sh','freeze-after-warning.sh','restart-after-warning.py']):
    host.upload(here/name,dest+'/'+name);host.ssh('cp '+dest+'/'+name+' /tmp/k211-'+name)
script='finish-quiesce-crtc-after-warning.sh' if from_crtc else 'continue-quiesce-after-warning.sh'
p=host.ssh('sh '+dest+'/'+script,timeout=150);(host.PRIVATE/'quiesce-recovery-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('cat /var/lib/samurai/k211-quiesce/quiesce-validation.json');proof=json.loads(p.stdout);assert proof['quiesce_audit_pass'] and proof['taint']==512 and proof['known_captured_mclk_warnings']==2
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
native=r'''
from pathlib import Path
import hashlib,json,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
targets=[p for p in root.iterdir() if p.name.startswith('k211') and p.is_dir() and not p.is_symlink()];targets.append(root/'gnss-assist')
files={str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for p in targets for q in p.rglob('*') if q.is_file() and not q.is_symlink()}
destination=Path('/tmp/k211-before-reboot-private.tar.gz');assert not destination.exists()
with tarfile.open(destination,'w:gz') as archive:
    for p in targets:archive.add(p,arcname=p.name,recursive=True)
print(json.dumps(dict(path=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=90);(host.PRIVATE/'before-reboot-manifest-private.json').write_bytes(p.stdout);record=json.loads(p.stdout)
target=host.PRIVATE/'before-reboot-private.tar.gz';assert not target.exists();host.download(record['path'],target);assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=211,full_quiesce=True,all_three_remoteprocs_offline=True,all_six_camera_modules_unloaded=True,known_mclk_warnings_preserved=2,taint=512,no_additional_or_other_warnings=True,private_archive_and_all_members_verified=True,archived_regular_files=len(members),no_transition_yet_sent=True)
(here/'pre-reboot-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
