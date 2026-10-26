from pathlib import Path
import hashlib, host, json, tarfile
here = Path(__file__).resolve().parent
reports = ['restore-bluetooth-baseline', 'query-pdc-readonly', 'query-pdc-details', 'test-tftp-isolated', 'deploy-tftp-ram', 'final-health']
for label in reports:
    value = json.loads((host.PRIVATE / (label + '-host-private.log')).read_text())
    (here / (label + '-validation.json')).write_text(json.dumps(value, indent=2) + '\n')
clean = json.loads((host.PRIVATE / 'tftp-clean-rebuild-r2/build-validation.json').read_text())
assert clean['candidate_sha256'] == json.loads((here / 'deploy-tftp-ram-validation.json').read_text())['binary_sha256']
(here / 'tftp-clean-rebuild-validation.json').write_text(json.dumps(clean, indent=2) + '\n')
native = r'''
from pathlib import Path
import hashlib,json,os,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205r2-runtime/boot-id-private.txt').read_bytes()
for p in Path('/proc').glob('[0-9]*'):
 try:
  cmd=(p/'cmdline').read_bytes()
  assert b'/var/lib/samurai/k206-gnss-context/test-geoclue-first-session.py' not in cmd
  assert b'/var/lib/samurai/k206-tftp-isolated/samurai-tqftpserv-isolated' not in cmd
 except FileNotFoundError:pass
reports={}
for prefix in ['k205','k206']:
 targets=sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix))
 destination=root/('k206-archive-'+prefix+'-private.tar.gz');assert not destination.exists()
 files={str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for p in targets for q in p.rglob('*') if q.is_file() and not q.is_symlink()}
 with tarfile.open(destination,'w:gz') as archive:
  for p in targets:archive.add(p,arcname=p.name,recursive=True)
 reports[prefix]=dict(archive=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)
print(json.dumps(reports))
'''
p = host.ssh('python3 -', input=native.encode(), timeout=100)
(host.PRIVATE / 'evidence-export-manifest-private.json').write_bytes(p.stdout)
records = json.loads(p.stdout)
summary = {}
for prefix, record in records.items():
    target = host.PRIVATE / (prefix + '-evidence-private.tar.gz')
    host.download(record['archive'], target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == record['sha256']
    members = {}
    with tarfile.open(target) as archive:
        for item in archive.getmembers():
            if item.isfile():
                members[item.name] = hashlib.sha256(archive.extractfile(item).read()).hexdigest()
    assert members == record['files']
    summary[prefix] = dict(regular_files=len(members), archive_hash_verified=True, all_regular_member_hashes_verified=True)
(here / 'evidence-export-validation.json').write_text(json.dumps(dict(stage=206, exports=summary, private_archive_hashes_not_published=True), indent=2) + '\n')
print(json.dumps(summary))
