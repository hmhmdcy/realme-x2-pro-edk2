from pathlib import Path
import hashlib,json,tarfile,host

here=Path(__file__).resolve().parent
health=json.loads((here/'final-health-validation.json').read_text())
assert health['same207_second_boot_verified'] and health['nmea_mask_independently_verified']==63
native=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
for p in Path('/proc').glob('[0-9]*'):
    try:assert b'/var/lib/samurai/k208-loc-tools/capture-debug-nmea' not in (p/'cmdline').read_bytes()
    except FileNotFoundError:pass
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==2
targets=sorted(p for p in root.iterdir() if p.name.startswith('k208') and not p.is_symlink() and (p.is_dir() or p.is_file()))
targets.append(root/'gnss-assist')
destination=root/'k208-native-evidence-private.tar.gz';assert not destination.exists()
files={}
for p in targets:
    for q in (p.rglob('*') if p.is_dir() else [p]):
        if q.is_file() and not q.is_symlink():files[str(q.relative_to(root))]=hashlib.sha256(q.read_bytes()).hexdigest()
with tarfile.open(destination,'w:gz') as archive:
    for p in targets:archive.add(p,arcname=p.name,recursive=True)
print(json.dumps(dict(archive=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=90)
(host.PRIVATE/'evidence-export-manifest-private.json').write_bytes(p.stdout)
record=json.loads(p.stdout);target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists()
host.download(record['archive'],target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={item.name:hashlib.sha256(archive.extractfile(item).read()).hexdigest() for item in archive.getmembers() if item.isfile()}
assert members==record['files']
report=dict(stage=208,regular_files=len(members),archive_hash_verified=True,all_regular_member_hashes_verified=True,private_nmea_and_archive_fingerprints_not_published=True)
(here/'evidence-export-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
