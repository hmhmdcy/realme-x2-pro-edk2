"""Atomically deploy the verified A640 candidate, preserving the original."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess

p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
os.umask(0o077)
base=Path('/var/lib/samurai/k148-mesa')
target=Path('/usr/lib/libvulkan_freedreno.so')
candidate=base/'candidate-build/libvulkan_freedreno.so'
expected_original='c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955'
expected_candidate='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(candidate)==expected_candidate
assert not target.is_symlink() and digest(target)==expected_original
assert subprocess.check_output(['uname','-v'],text=True).startswith('#147 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for label in ['candidate-holes','candidate-hole-formats']:
    out=Path('/var/lib/samurai')/('k149-'+label)
    r=json.loads((out/'result.json').read_text())
    assert r['exit']==0 and not r['error'] and r['before']==r['after']
    assert r['desktop_preserved'] and r['boot_preserved'] and r['taint']=='0'
    assert r['unaligned64k_maps']==0 and r['failed_bind_ops']==0
    assert (out/'boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
failure=Path('/var/lib/samurai/k149-installed-gmem-holes')
r=json.loads((failure/'result.json').read_text())
assert r['exit']==2 and r['core_saved']==1 and not r['capture_errors']
assert r['after']['gpu_faults']==r['before']['gpu_faults']+1
assert r['driver_library_sha256']==expected_original
assert (failure/'boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
out=Path('/var/lib/samurai/k149-deployment')
backup=out/'libvulkan_freedreno.so.original'
manifest=dict(actual_kernel=147,original_sha256=expected_original,candidate_sha256=expected_candidate,
    package='mesa-vulkan-freedreno-26.2.4-r1',deployment='local patched library',
    package_database_modified=False,automatic_package_upgrade_can_replace_patch=True)
if not a.apply:
    print(json.dumps(dict(preflight_passed=True,**manifest)))
    raise SystemExit(0)
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
shutil.copy2(target,backup)
assert digest(backup)==expected_original
fixed=out/'libvulkan_freedreno.so.fixed';shutil.copy2(candidate,fixed)
assert digest(fixed)==expected_candidate
for name in ['/lib/apk/db/installed','/etc/greetd/samurai-phosh.toml']:
    manifest[Path(name).name+'_sha256']=digest(Path(name))
temporary=target.with_name('.libvulkan_freedreno.so.k149-stage')
assert not temporary.exists()
try:
    with temporary.open('xb') as f:
        f.write(candidate.read_bytes());f.flush();os.fsync(f.fileno())
    os.chmod(temporary,0o755);os.chown(temporary,0,0)
    assert digest(temporary)==expected_candidate
    temporary.replace(target)
    fd=os.open(str(target.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    assert digest(target)==expected_candidate
    manifest.update(applied=True,original_backup_verified=True,atomic_replace=True)
except BaseException:
    if temporary.exists():temporary.unlink()
    raise
(out/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
subprocess.run(['sync'],check=True)
print(json.dumps(manifest))
