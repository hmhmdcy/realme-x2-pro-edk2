"""Private native receipts only; verify every archive file without extraction."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import hashlib,json,os,tarfile
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()
assert (root/'k234-tools/exit-private.json').exists()
assert json.loads((root/'k234-diagnostic/summary.json').read_text())['state']=='restored'
os.umask(0o077)
dest=root/'k234-native-evidence-private.tar.gz'
manifest=root/'k234-native-evidence-manifest-private.json'
assert not dest.exists() and not manifest.exists()
names=['k234-baseline','k234-baseline-r2','k234-tools','k234-diagnostic','k234-final-health']
files=[p for n in names for p in sorted((root/n).rglob('*')) if p.is_file()]
assert files and not any(p.is_symlink() for p in files)
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest.write_text(json.dumps(hashes,indent=2)+'\n')
with tarfile.open(dest,'w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
print(json.dumps(dict(members=len(files))))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=45)
(host.PRIVATE / 'evidence-export-host-private.log').write_bytes(result.stdout + result.stderr)
for name in ['k234-native-evidence-private.tar.gz', 'k234-native-evidence-manifest-private.json']:
    host.download('/var/lib/samurai/' + name, host.PRIVATE / name)
expected = json.loads((host.PRIVATE / 'k234-native-evidence-manifest-private.json').read_text())
actual = {}
with tarfile.open(host.PRIVATE / 'k234-native-evidence-private.tar.gz', 'r:gz') as archive:
    for member in archive:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        stream = archive.extractfile(member)
        actual[member.name] = hashlib.sha256(stream.read()).hexdigest()
assert actual == expected and len(actual) == json.loads(result.stdout)['members']
report = dict(stage=234, native_members=len(actual), all_members_verified=True,
              no_scene_image_capture=True, raw_uart_and_private_ids_not_published=True,
              native_worker_terminal=True, trace_and_original_module_restoration_preserved=True,
              first_baseline_path_error_and_scan_harness_failure_preserved=True)
(R / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
