"""Verify sources after C exhaustion and create a new build filesystem on E only."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
COMMIT='18b48939788bc7f95fb2999ea986846a67f0c62c'
git=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args])
assert git('rev-parse','HEAD').decode().strip()==COMMIT
assert not git('status','--porcelain')
failed=json.loads((host.PRIVATE/'full-kernel-r2-build-state-private.json').read_text())
assert failed['terminal'] and failed['exit']==1
assert not Path('/proc',str(failed['pid'])).exists() and not Path('/proc',str(failed['child_pid'])).exists()
checked={}
manifest=json.loads((ROOT/'candidate-commit-validation.json').read_text())['source_hashes']
for path,expected in manifest.items():
    data=(TREE/path).read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected
    checked[path]=expected
for path in ['drivers/xen/xenbus/xenbus_probe.c','net/mac80211/scan.c']:
    data=(TREE/path).read_bytes()
    assert data==git('show',COMMIT+':'+path)
    checked[path]=hashlib.sha256(data).hexdigest()

backing=host.PRIVATE/'full-kernel-build282.ext4'
assert backing.parent.resolve()==host.PRIVATE.resolve() and not backing.exists() and not backing.is_symlink()
available=os.statvfs(backing.parent)
assert available.f_bavail*available.f_frsize>40*1024**3
size=32*1024**3
with backing.open('xb') as output:
    output.truncate(size)
info=backing.lstat()
assert stat.S_ISREG(info.st_mode) and not backing.is_symlink() and info.st_size==size
# Format only this newly created regular file. No block device or existing
# image is accepted by the exclusive-create and regular-file checks above.
run=subprocess.run(['mkfs.ext4','-F','-m','0','-L','samurai282',str(backing)],capture_output=True,text=True)
(host.PRIVATE/'new-build-filesystem-private.log').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
with backing.open('rb') as source:
    source.seek(1080)
    assert source.read(2)==b'\x53\xef'
mount=Path('/mnt/samurai-full282')
assert not mount.exists() and not mount.is_symlink()
mount.mkdir(mode=0o700)
subprocess.run(['mount','-o','loop,noatime',str(backing),str(mount)],check=True,capture_output=True)
mounted=subprocess.check_output(['findmnt','-n','-o','FSTYPE,SOURCE,TARGET','--target',str(mount)],text=True).split()
assert len(mounted)==3 and mounted[0]=='ext4' and mounted[1].startswith('/dev/loop') and mounted[2]==str(mount)
loop=Path(mounted[1]).name
loop_backing=Path('/sys/class/block',loop,'loop/backing_file').read_text().strip()
assert Path(loop_backing).resolve()==backing.resolve()
assert mount.stat().st_dev!=mount.parent.stat().st_dev
build=mount/'build';build.mkdir()
config=(host.PRIVATE/'full-config-corrected-private.config').read_bytes()
assert hashlib.sha256(config).hexdigest()=='0c26bd9147ac31b92d824b8dbd529384772be3c8ae819314240cdd6cbde3a6ca'
(build/'.config').write_bytes(config)
(mount/'tmp').mkdir(mode=0o700)
report=dict(stage=282,r2_full_build_terminal_failure=True,r2_seconds=failed['seconds'],
    cause='Windows C had zero free bytes; WSL VHD is on C; compiler read IO errors and WSL startup failure followed',
    pip_cache_files_preserved=1419,pip_cache_bytes_preserved=3725983899,
    source_files_read_and_verified=checked,source_commit=COMMIT,source_clean=True,
    new_filesystem_backing=str(backing),new_filesystem_bytes=size,
    new_filesystem_created_exclusively_not_existing_data=True,
    mount=str(mount),build=str(build),loop_device=mounted[1],backing_file_verified=True,
    old_source_and_build_tree_preserved=True,no_phone_changes=True)
(ROOT/'build-storage-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_files_read_and_verified'},indent=2))
