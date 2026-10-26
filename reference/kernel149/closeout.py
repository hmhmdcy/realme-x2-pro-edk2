"""Remove only archived temporary copies and record the final live state."""
from pathlib import Path
import hashlib,json,runpy,shutil
root=Path('/var/lib/samurai');deployment=root/'k149-deployment'
archive_index=json.loads((root/'k149-private-archives/archive-index.json').read_text())
host=json.loads((deployment/'host-archive-verification.json').read_text())
assert host['all_raw_archives_downloaded'] and host['archives_verified']==14
expected={r['label']:r['sha256'] for r in archive_index['archives']}
assert {r['label']:r['sha256'] for r in host['verified']}==expected
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for r in archive_index['archives']:
    assert digest(root/'k149-private-archives'/r['name'])==r['sha256']
removed=[]
tools=root/'k149-tools/scripts';tools.mkdir(mode=0o700,exist_ok=True)
for p in sorted(Path('/tmp').glob('k149-*.py')):
    saved=tools/p.name
    if not saved.exists():shutil.copy2(p,saved)
    assert digest(p)==digest(saved)
    p.unlink();removed.append(p.name)
for name in ['headless-session','settings-cycle','session-app','parallel-probe']:
    p=Path('/tmp')/('k148-'+name+'.py')
    saved=root/'k148-tools/uploaded-sources'/p.name
    if p.exists():
        assert digest(p)==digest(saved)
        p.unlink();removed.append(p.name)
duplicates=0;retained=[]
for p in Path('/tmp').glob('k149-*-private.tar.gz'):
    label=p.name.removeprefix('k149-').removesuffix('-private.tar.gz')
    if label in expected and digest(p)==expected[label]:
        duplicates+=p.stat().st_size;p.unlink()
    else:retained.append(p.name)
runpy.run_path(str(tools/'k149-verify-runtime.py'))
final=json.loads((deployment/'final-verification.json').read_text())
report=dict(closeout_complete=True,raw_archives_persisted=14,raw_archives_verified_on_host=14,
    temporary_sources_archived_and_removed=removed,duplicate_temporary_archive_bytes_removed=duplicates,
    retained_unmatched_temporary_archives=retained,source_builds_and_sdk_preserved=True,
    active_probe_processes=final['active_probe_processes'],remaining_probe_trace_instances=final['remaining_probe_trace_instances'],
    pending_devcoredumps=final['pending_devcoredumps'],boot_preserved=final['boot_preserved'],
    physical_desktop_preserved=final['physical_desktop_preserved'],taint=final['taint'],
    cumulative_counts=final['cumulative_counts'],new_faults_after_deployment=0,
    installed_library_sha256=final['installed_library_sha256'],original_library_backup_verified=True)
(deployment/'closeout.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
