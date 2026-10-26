"""One transaction restoring the verified Linux image to its sole userdata target."""
from pathlib import Path
import os,sys,stat,json,hashlib,subprocess,time,re,traceback,shutil
ROOT=Path('/run/k257-restore');ROOT.mkdir(exist_ok=True)
STATE=ROOT/'state.json';assert not STATE.exists()
state=dict(stage=257,state='starting',terminal=False,target='/dev/sda16',write_started=False)
def save(phase,**values):
    state.update(state=phase,**values);tmp=ROOT/'state.tmp';tmp.write_text(json.dumps(state)+'\n');os.replace(tmp,STATE)
def command(args,log):
    with (ROOT/log).open('wb') as out:
        return subprocess.run(args,stdout=out,stderr=out).returncode
target=Path('/dev/sda16');mounted=False;children=[]
try:
    save('checking_guards')
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/run/k257-rescue-boot-id-private.txt').read_bytes()
    assert '#183 ' in os.uname().version
    fsck=shutil.which('fsck.f2fs');assert fsck
    assert Path('/usr/sbin/partclone.restore').is_file() and Path('/usr/bin/zstd').is_file()
    assert stat.S_ISBLK(target.stat().st_mode)
    assert int(Path('/sys/class/block/sda16/size').read_text())*512==119033245696
    assert int(Path('/sys/class/block/sda16/start').read_text())*512==7370473472
    assert 'PARTNAME=userdata\n' in Path('/sys/class/block/sda16/uevent').read_text()
    device=f'{os.major(target.stat().st_rdev)}:{os.minor(target.stat().st_rdev)}'
    assert not any(line.split()[2]==device for line in Path('/proc/self/mountinfo').read_text().splitlines())
    assert Path('/sys/class/block/sda16/ro').read_text().strip()=='1'
    image=Path('/run/k257-image/backup.pcl.zst')
    assert image.stat().st_size==4589045416
    save('verifying_ram_source')
    assert hashlib.file_digest(image.open('rb'),'sha256').hexdigest()=='01fe9f0ba9bfb13ae14ed2e704152c7b3061be5193e70c3930d68be83668671e'
    image.chmod(0o400)
    save('before_userdata_write',full_compressed_sha_verified=True)
    assert command(['/bin/busybox','blockdev','--setrw',str(target)],'setrw.log')==0
    assert Path('/sys/class/block/sda16/ro').read_text().strip()=='0'
    save('restoring_userdata',write_started=True)
    with (ROOT/'restore-stdout.log').open('wb') as out,(ROOT/'zstd-stderr.log').open('wb') as err:
        z=subprocess.Popen(['/usr/bin/zstd','-d','-c',str(image)],stdout=subprocess.PIPE,stderr=err)
        children.append(z)
        restore=subprocess.Popen(['/usr/sbin/partclone.restore','-s','-','-O',str(target),'-L',str(ROOT/'partclone.log')],stdin=z.stdout,stdout=out,stderr=out)
        children.append(restore);z.stdout.close()
        restore_rc=restore.wait();zstd_rc=z.wait()
    save('restore_processes_returned',partclone_exit_code=restore_rc,zstd_exit_code=zstd_rc)
    assert restore_rc==zstd_rc==0
    os.sync();fd=os.open(target,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    assert command(['/bin/busybox','blockdev','--setro',str(target)],'setro.log')==0
    assert Path('/sys/class/block/sda16/ro').read_text().strip()=='1'
    save('checking_f2fs_read_only')
    rc=command([fsck,'--dry-run','--no-kernel-check','-f',str(target)],'fsck.log')
    save('f2fs_check_returned',fsck_exit_code=rc);assert rc==0
    mountpoint=Path('/mnt/k257-linux');mountpoint.mkdir(parents=True,exist_ok=True)
    assert command(['/bin/busybox','mount','-t','f2fs','-o','ro,norecovery',str(target),str(mountpoint)],'mount.log')==0
    mounted=True
    marker=mountpoint/'etc/samurai-rootfs-release';assert marker.is_file()
    assert hashlib.sha256(marker.read_bytes()).hexdigest()==sys.argv[1]
    installed=next(candidate for candidate in [mountpoint/'lib/apk/db/installed',mountpoint/'usr/lib/apk/db/installed']
        if candidate.is_file() and candidate.resolve().is_relative_to(mountpoint))
    package_count=len(re.findall(rb'^P:',installed.read_bytes(),re.M))
    release=(mountpoint/'etc/alpine-release').read_text().strip()
    profile_dir=mountpoint/'etc/NetworkManager/system-connections'
    profiles=len(list(profile_dir.glob('*'))) if profile_dir.is_dir() else 0
    report=dict(stage=257,source_compressed_bytes=4589045416,full_compressed_sha_verified=True,
        target='/dev/sda16',target_bytes=119033245696,partition_start_and_size_verified=True,
        partclone_exit_code=restore_rc,zstd_exit_code=zstd_rc,fsck_dry_run_exit_code=rc,
        original_linux_root_marker_sha_matches=True,restored_package_count=package_count,
        restored_alpine_release=release,restored_wifi_profile_files=profiles,
        no_gpt_nv_persist_or_calibration_target=True)
    (ROOT/'summary.json').write_text(json.dumps(report)+'\n')
    assert command(['/bin/busybox','umount',str(mountpoint)],'unmount.log')==0;mounted=False
    save('complete',terminal=True,exit_code=0,userdata_unmounted=True,userdata_readonly=True)
except BaseException as error:
    for child in children:
        if child.poll() is None:child.terminate()
    for child in children:
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
    (ROOT/'exception-private.log').write_text(traceback.format_exc())
    save('failed',terminal=True,exit_code=1,error_type=type(error).__name__)
    raise
finally:
    if mounted:subprocess.run(['/bin/busybox','umount','/mnt/k257-linux'],capture_output=True)
    subprocess.run(['/bin/busybox','blockdev','--setro',str(target)],capture_output=True)
