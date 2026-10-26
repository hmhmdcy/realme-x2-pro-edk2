"""One bounded Image505 trial. A failed userspace trial restores both carriers.

Recovery requires Linux userspace to run; it cannot recover a pre-userspace hang.
No module unloading, charger register writes, or gauge diagnostic commands.
"""
from pathlib import Path
import fcntl, hashlib, json, os, stat, subprocess, sys, time

ROOT=Path('/root/charging-management-20261023/image505-trial-20261025-01')
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION='#505 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
HELPER='/usr/lib/samurai-charging/image505-boot-guard.py'
USB='/lib/modules/'+RELEASE+'/extra/samurai-charging/samurai-usb-input.ko'
ALLOWED={USB,'/usr/share/samurai-charging/manifest.json','/etc/init.d/samurai-charging',HELPER}
ALLOWED.update('/lib/modules/'+RELEASE+'/'+n for n in ['modules.builtin','modules.builtin.modinfo','modules.builtin.bin','modules.builtin.alias.bin'])
PARTS={'boot':('/dev/disk/by-partlabel/boot',100663296),'logdump':('/dev/disk/by-partlabel/logdump',67108864)}

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def regular(path):
    info=Path(path).lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022
    return info

def atomic(path,raw,mode=0o600):
    path=Path(path);tmp=path.with_name(path.name+'.image505-next')
    assert not tmp.exists() and not tmp.is_symlink()
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fchmod(stream.fileno(),mode);os.fsync(stream.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def state(event,**values):
    atomic(ROOT/'state.json',(json.dumps(dict(event=event,boot=boot(),boottime=time.clock_gettime(time.CLOCK_BOOTTIME),**values))+'\n').encode())

def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

def load():
    info=ROOT.lstat();assert stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode&0o077
    regular(ROOT/'meta.json');meta=json.loads((ROOT/'meta.json').read_bytes())
    assert set(meta['files'])==ALLOWED and set(meta['parts'])==set(PARTS)
    assert digest(ROOT/'new'/HELPER.lstrip('/'))==meta['recovery_helper_sha256']
    for path,row in meta['files'].items():
        for side in ['old','new']:
            if row[side] is None:continue
            p=ROOT/side/path.lstrip('/');regular(p);assert digest(p)==row[side]['sha256']
    for name,row in meta['parts'].items():
        for side in ['old','new']:
            p=ROOT/side/(name+'.img');regular(p)
            assert p.stat().st_size==PARTS[name][1] and digest(p)==row[side]
    return meta

def partition_identity(device):
    device=Path(device).resolve(strict=True);sysfs=Path('/sys/class/block')/device.name
    uuids=sorted(p.name for p in Path('/dev/disk/by-partuuid').iterdir() if p.resolve()==device)
    assert len(uuids)==1
    return dict(partuuid=uuids[0],start=int((sysfs/'start').read_text()),sectors=int((sysfs/'size').read_text()),partition=int((sysfs/'partition').read_text()))

def target_hash(path):
    p=Path(path)
    if not p.exists():assert not p.is_symlink();return None
    regular(p);return digest(p)

def restore_files(meta):
    # Original helper absence is handled last, after all reusable state is restored.
    for path,row in sorted(meta['files'].items(),key=lambda item:item[0]==HELPER):
        present=target_hash(path);accepted={r['sha256'] for r in [row['old'],row['new']] if r}
        assert present in accepted or present is None and row['old'] is None,(path,'unexpected file')
        if row['old'] is None:
            if present is not None:Path(path).unlink()
        else:
            old=row['old'];atomic(path,(ROOT/'old'/path.lstrip('/')).read_bytes(),old['mode'])
            os.chown(path,old['uid'],old['gid']);assert digest(path)==old['sha256']

def write_part(meta,name,side):
    alias,size=PARTS[name];device=Path(alias).resolve(strict=True)
    assert stat.S_ISBLK(device.stat().st_mode)
    assert partition_identity(device)==meta['partition_identity'][name]
    major_minor=f'{os.major(device.stat().st_rdev)}:{os.minor(device.stat().st_rdev)}'
    assert int(Path('/sys/dev/block',major_minor,'size').read_text())*512==size
    mounted={line.split()[0] for line in Path('/proc/mounts').read_text().splitlines()}
    assert str(device) not in mounted and alias not in mounted
    current=digest(device)
    if side=='new':assert current in {meta['parts'][name]['old'],meta['parts'][name]['new']}
    if current==meta['parts'][name][side]:return
    with (ROOT/side/(name+'.img')).open('rb') as source,device.open('r+b',buffering=0) as target:
        remaining=size
        while remaining:
            block=source.read(min(1024*1024,remaining));assert block
            view=memoryview(block)
            while view:
                count=target.write(view);assert count and count>0;view=view[count:]
            remaining-=len(block)
        assert not source.read(1);os.fsync(target.fileno())
    assert digest(device)==meta['parts'][name][side],(name,'readback')

def rollback(meta,reason,restart):
    state('restoring',reason=reason)
    # Old firmware first: never pair the new Type-C DT with the old kernel.
    write_part(meta,'boot','old');write_part(meta,'logdump','old')
    restore_files(meta);state('restored',reason=reason);os.sync()
    if restart:subprocess.run(['/sbin/reboot'],check=True)

def acknowledged(meta):
    p=ROOT/'accepted.json'
    if not p.exists():return False
    regular(p);a=json.loads(p.read_bytes())
    return a==dict(boot=boot(),token=meta['token'],manifest=meta['files']['/usr/share/samurai-charging/manifest.json']['new']['sha256'])

def prestart(meta):
    version=Path('/proc/version').read_text()
    if VERSION not in version or os.uname().release!=RELEASE:
        rollback(meta,'unexpected-kernel',False);return
    if acknowledged(meta):return
    lock=os.open(ROOT/'watchdog.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state('watchdog-starting')
        with (ROOT/'watchdog.stdout').open('ab') as out,(ROOT/'watchdog.stderr').open('ab') as err:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'new'/HELPER.lstrip('/')),'watch'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True,pass_fds=(lock,),env={**os.environ,'IMAGE505_LOCK_FD':str(lock)})
        state('watchdog-running',pid=child.pid)
    except BlockingIOError:pass
    finally:os.close(lock)

def watch(meta):
    lock=int(os.environ['IMAGE505_LOCK_FD']);assert os.fstat(lock).st_uid==0
    deadline=time.clock_gettime(time.CLOCK_BOOTTIME)+300
    while time.clock_gettime(time.CLOCK_BOOTTIME)<deadline:
        if acknowledged(meta):state('accepted');return
        time.sleep(2)
    rollback(meta,'no-healthy-host-adoption-within-300s',True)

def main():
    os.umask(0o077);assert os.geteuid()==0
    meta=load();action=sys.argv[1]
    if action=='prestart':prestart(meta)
    elif action=='watch':watch(meta)
    elif action=='restore':rollback(meta,'explicit-recovery',False)
    elif action=='check':print(json.dumps(dict(passed=True,files=len(meta['files']),images_verified=True)))
    else:raise ValueError(action)

if __name__=='__main__':main()
