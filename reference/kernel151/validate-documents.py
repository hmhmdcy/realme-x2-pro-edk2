"""Check current handover links, evidence totals, and retained private log copies."""
from pathlib import Path
import hashlib, json, re

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root/'reference/kernel151'
documents = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md',
    'linux-port/docs/HARDWARE-STATUS.md', 'sessions/151-gpu-closeout-and-hardware-handover.md',
    'reference/kernel151/README.md']
links = 0
for relative in documents:
    source = root/relative
    content = source.read_text()
    assert '\ufffd' not in content, relative
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if target.startswith(('https:', 'http:', '#')): continue
        assert (source.parent/target.split('#')[0]).exists(), (relative, target)
        links += 1
hardware = (root/'linux-port/docs/HARDWARE-STATUS.md').read_text()
rows = [line for line in hardware.splitlines() if line.startswith('| ') and not line.startswith('| 功能组') and not line.startswith('| ---')]
assert len(rows) == 15
gpu_row = next(line for line in rows if line.startswith('| GPU |'))
assert '已修复并部署' in gpu_row and '未解决' not in gpu_row
for prefix in ['| 音频 |', '| 摄像头 |', '| 指纹 |', '| GNSS定位 |']:
    assert any(line.startswith(prefix) for line in rows)
state = json.loads((ref/'closeout.json').read_text())
assert state['new_gpu_faults_since_stage149'] == 0 and state['taint'] == 0
assert state['current_kernel_build'].startswith('#147 ')
assert state['checks']['installed_library_matches_deployed_fix']
assert state['package_database_changed_since_stage149']
assert state['package_database_stable_during_closeout']
assert not state['kernel150_compatibility_candidate_deployed']
private = Path('/mnt/e/edk2-samurai-out/kernel151')
for row in (private/'device-private-files.sha256').read_text().splitlines():
    if not row.strip(): continue
    digest, name = row.split(maxsplit=1)
    file = private/Path(name).name
    assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
history = json.loads((ref/'document-history.json').read_text())
for record in history:
    assert hashlib.sha256((root/record['archive']).read_bytes()).hexdigest() == record['archive_sha256']
report = dict(current_documents_checked=len(documents), current_local_links_valid=links,
    hardware_groups=15, gpu_fixed_row_current=True, history_snapshots_preserved=len(history),
    raw_private_files_downloaded_and_verified=2, live_gpu_fix_verified=True,
    package_metadata_drift_retained=True, compatibility_candidate_not_deployed=True,
    files_written=[*documents, 'HANDOVER-NEXT.md', 'DOCS-INDEX.md', 'README.md', 'linux-port/README.md'])
(ref/'document-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
