"""Archive finished stage-148 work; no GPU workload or driver deployment."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess, tarfile

os.umask(0o077)
base=Path('/var/lib/samurai')
out=base/'k148-closeout'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(base/'k147-closeout/boot-id-private.txt').read_bytes()
watch=base/'k148-fault-watch-oct13'
assert boot==(watch/'boot-id-private.txt').read_bytes()
watch_status=json.loads((watch/'status.json').read_text())
assert watch_status['active'] is False
watch_pid=int((watch/'watch-pid-private.txt').read_text())
watch_cmd=Path(f'/proc/{watch_pid}/cmdline')
assert not watch_cmd.exists() or b'k148-fault-watch.py' not in watch_cmd.read_bytes()

active=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
    try:argv=proc.joinpath('cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    exe=Path(os.fsdecode(argv[0])).name if argv and argv[0] else ''
    python_job=len(argv)>1 and exe.startswith('python') and b'/tmp/k148-' in argv[1]
    probe_job=exe in ['vulkan-pixel-probe','vulkan-memory-probe']
    if python_job or probe_job:active.append(proc.name)
assert not active, 'Stage-148 workload still running'
assert not list(Path('/sys/kernel/tracing/instances').glob('k148-*'))
desktop={name:subprocess.check_output(['pgrep','-x',name],text=True).strip() for name in ['phoc','phosh']}
assert desktop=={'phoc':'28677','phosh':'28750'}
if out.exists():
    assert (out/'boot-id-private.txt').read_bytes()==boot
    assert not (out/'closeout-public.json').exists(), 'Closeout already completed'
out.mkdir(mode=0o700,exist_ok=True)
out.joinpath('boot-id-private.txt').write_bytes(boot)
out.joinpath('desktop-pids-private.json').write_text(json.dumps(desktop)+'\n')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

checks=subprocess.run(['sha256sum','-c',str(base/'k148-sdk-apks/packages-before.sha256')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
out.joinpath('package-verification-private.txt').write_text(checks.stdout)
driver=Path('/usr/lib/libvulkan_freedreno.so')
installed_sha=sha(driver)
assert installed_sha=='c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955'
greetd_sha=sha(Path('/etc/greetd/samurai-phosh.toml'))
assert greetd_sha=='ff7c25efe841ebe811ed6674f1600f5439cd6169f2dca7d26c1037c9e218ffec'
libraries={}
for kind,expected in [('baseline','e5841c3abd9bd5ddaf2324a4be55df3fdf462e896104f96166bead8904763110'),('candidate','97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e')]:
    libraries[kind]=sha(base/f'k148-mesa/{kind}-build/libvulkan_freedreno.so')
    assert libraries[kind]==expected

labels=[]
for f in sorted(base.glob('k148-*/result.json')):
    row=json.loads(f.read_text())
    if all(k in row for k in ['label','before','after']):
        assert row['label'].replace('-','').isalnum()
        labels.append(row['label'])
archives=base/'k148-private-archives'
archives.mkdir(mode=0o700,exist_ok=True)
archive_rows=[];freed=0
for label in sorted(set(labels+['entry'])):
    src=Path('/tmp')/f'k148-{label}-private.tar.gz'
    dst=archives/src.name
    if src.exists():
        assert src.is_file() and not src.is_symlink() and src.resolve().parent==Path('/tmp')
        digest=sha(src)
        if dst.exists():assert dst.is_file() and not dst.is_symlink() and sha(dst)==digest
        else:
            with src.open('rb') as a,dst.open('xb') as b:
                shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
            assert sha(dst)==digest
        freed+=src.stat().st_size
        src.unlink()
    if dst.exists():archive_rows.append(dict(label=label,bytes=dst.stat().st_size,sha256=sha(dst)))
out.joinpath('archive-index.json').write_text(json.dumps(archive_rows,indent=2)+'\n')

# Preserve the uploaded source fragments before removing only those task files.
scripts=base/'k148-tools/uploaded-sources'
scripts.mkdir(mode=0o700,exist_ok=True)
removed=[]
for src in sorted(Path('/tmp').glob('k148-*')):
    if src.suffix not in ['.py','.c','.vert','.frag'] or not src.is_file() or src.is_symlink():continue
    dst=scripts/src.name
    if dst.exists():assert dst.is_file() and not dst.is_symlink() and sha(dst)==sha(src)
    else:
        with src.open('rb') as a,dst.open('xb') as b:shutil.copyfileobj(a,b)
        assert sha(dst)==sha(src)
    src.unlink();removed.append(src.name)

dmesg=subprocess.check_output(['dmesg'],text=True)
out.joinpath('dmesg-final-private.txt').write_text(dmesg)
faults={k:dmesg.count(v) for k,v in {'gpu_faults':'gpu fault:','warnings':'WARNING:','dpu_timeouts':'frame done timeout','dsi_errors':'dsi_err_worker','dma_prepare':'unable to prepare channel'}.items()}
compiler={}
for f in sorted((base/'k148-tools').glob('*compiler-private.log')):
    text=f.read_text(errors='replace')
    compiler[f.name]=dict(warnings=text.count('warning:'),errors=text.count('error:'))
out.joinpath('compiler-summary.json').write_text(json.dumps(compiler,indent=2)+'\n')
report=dict(stage=148,status='closed_out',recorded_at=datetime.now(timezone.utc).isoformat(),
    gpu_fix_complete=False,candidate_promoted=False,boot_preserved=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
    desktop_preserved=desktop=={n:subprocess.check_output(['pgrep','-x',n],text=True).strip() for n in desktop},
    kernel_release=subprocess.check_output(['uname','-r'],text=True).strip(),taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
    cumulative_fault_counts=faults,installed_driver_sha256=installed_sha,diagnostic_libraries_sha256=libraries,
    package_database_preserved=True,greetd_config_preserved=True,watcher=watch_status,
    watcher_fault_counts=json.loads((watch/'fault-counts.json').read_text()),
    active_test_processes=0,remaining_test_trace_instances=0,archived_test_runs=len(labels),
    persistent_private_archives=len(archive_rows),temporary_archive_bytes_reclaimed=freed,
    uploaded_source_files_preserved_and_removed=len(removed),sdk_preserved=True,
    source_and_builds_preserved=True)
out.joinpath('closeout-public.json').write_text(json.dumps(report,indent=2)+'\n')
out.joinpath('cleanup-files-private.json').write_text(json.dumps(removed,indent=2)+'\n')
assert report['boot_preserved'] and report['desktop_preserved']
out.joinpath('SHA256SUMS').write_text(''.join(sha(f)+'  ./'+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))

# Receipt-only bundle; complete raw GPU archives remain in persistent storage.
bundle=archives/'k148-closeout-receipts-private.tar.gz'
with tarfile.open(bundle,'x:gz') as t:
    for folder in [out,watch,scripts]:t.add(folder,arcname=folder.relative_to(base))
    for f in sorted(base.glob('k148-*/result.json')):t.add(f,arcname=f.relative_to(base))
bundle.with_name(bundle.name+'.sha256').write_text(sha(bundle)+'\n')
print(json.dumps(report))
