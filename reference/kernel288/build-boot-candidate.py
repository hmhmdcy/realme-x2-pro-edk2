"""Build a coherent candidate with the verified boot/recovery input and matching modules."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,shutil,stat,subprocess,sys,tarfile,time,zlib

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
COMMIT='8c79b7e1912790d3e18a84c9c6621a6d92baa768'
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
marker=PRIVATE/'boot-candidate-state-private.json';assert not marker.exists()
old=json.loads((ROOT/'pix-full-build-validation.json').read_text())
backup=PRIVATE/'completed-compile-pix288';assert not backup.exists();backup.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,row in old['artifacts'].items():
    assert sha(BUILD/name)==row['sha256']
    shutil.copyfile(BUILD/name,backup/Path(name).name)

original=Path('/home/cy122/pmos-samurai-kernel136/initramfs')
payload=BUILD.parent/'input-initramfs288'
assert original.is_dir() and not original.is_symlink() and not payload.exists()
subprocess.run(['cp','-a',str(original),str(payload)],check=True)
def snapshot(root):
    rows={}
    for p in root.rglob('*'):
        info=p.lstat();row=dict(mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid)
        if p.is_symlink():row.update(kind='symlink',target=os.readlink(p))
        elif p.is_file():row.update(kind='file',sha256=sha(p))
        elif p.is_dir():row.update(kind='directory')
        else:row.update(kind='special',rdev=info.st_rdev)
        rows[str(p.relative_to(root))]=row
    return rows
initial=snapshot(original);assert initial==snapshot(payload)
# Anchor the actual boot scripts and authentication to the preserved deployed Image183.
image183=PRIVATE.parent/'kernel183/Image-k183-offline-stream-private'
assert sha(image183)=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
raw=image183.read_bytes();archives=[]
for m in re.finditer(b'\x1f\x8b\x08',raw):
    try:
        dec=zlib.decompressobj(16+zlib.MAX_WBITS);b=dec.decompress(raw[m.start():],64*1024*1024)
        if b.startswith((b'070701',b'070702')) and b'TRAILER!!!' in b:archives.append(b)
    except zlib.error:pass
assert len(archives)==1
b=archives[0];pos=0;entries={}
while pos+110<=len(b):
    h=b[pos:pos+110];assert h[:6] in [b'070701',b'070702']
    values=[int(h[6+i*8:14+i*8],16) for i in range(13)]
    size,namesize=values[6],values[11];name=b[pos+110:pos+110+namesize-1].decode().removeprefix('./')
    start=(pos+110+namesize+3)&~3
    if name=='TRAILER!!!':break
    entries[name]=b[start:start+size];pos=(start+size+3)&~3
critical=['init','usr/sbin/samurai-rootfs','usr/sbin/samurai-usb','etc/dropbear/dropbear_ed25519_host_key','root/.ssh/authorized_keys']
for name in critical:assert (payload/name).read_bytes()==entries[name],name
assert b'/usr/sbin/samurai-rootfs' in entries['init']
assert b'switch_root' in entries['usr/sbin/samurai-rootfs'] and b'diagnostic fallback' in entries['usr/sbin/samurai-rootfs']
epoch=int(git('show','-s','--format=%ct',COMMIT))
module_changes=[]
for target in payload.rglob('*.ko'):
    name=target.name;found=list(BUILD.rglob(name));assert len(found)==1,(name,len(found))
    shutil.copyfile(found[0],target)
    subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(target)],check=True)
    os.utime(target,(epoch,epoch))
    vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).strip()
    assert vermagic.startswith('7.3.0-rc6-rmx1931-samurai-k279candidate+')
    module_changes.append(str(target.relative_to(payload)))
assert sorted(module_changes)==sorted(['lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']])
payload_manifest=snapshot(payload)
assert {n for n in initial if initial[n]!=payload_manifest[n]}==set(module_changes)
(PRIVATE/'boot-initramfs-manifest-private.json').write_text(json.dumps(payload_manifest,indent=2)+'\n')
before=(BUILD/'.config').read_text()
subprocess.run([str(TREE/'scripts/config'),'--file',str(BUILD/'.config'),'--set-str','INITRAMFS_SOURCE',str(payload)],check=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
         KBUILD_BUILD_VERSION='288',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
         KBUILD_BUILD_TIMESTAMP=datetime.fromtimestamp(epoch,timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),TMPDIR=str(BUILD.parent/'tmp'))
base=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1']
module_root=BUILD.parent/'modules288';assert not module_root.exists()
phases=[];begin=time.monotonic()
state=dict(stage=288,commit=COMMIT,terminal=False,worker=os.getpid())
for name,args in [('configure',['olddefconfig']),('image-modules',['Image','modules','qcom/sm8150-samurai.dtb']),
                  ('install-modules',['INSTALL_MOD_PATH='+str(module_root),'INSTALL_MOD_STRIP=1','modules_install'])]:
    start=time.monotonic();log=PRIVATE/('boot-'+name+'-private.log')
    with log.open('xb') as output:
        child=subprocess.Popen(base+args,env=env,stdout=output,stderr=subprocess.STDOUT)
        state.update(phase=name,child_pid=child.pid);marker.write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps(dict(phase=name,started=True,worker=os.getpid(),child=child.pid)),flush=True)
        ret=child.wait()
    diagnostics=[l for l in log.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
    phases.append(dict(name=name,exit=ret,seconds=round(time.monotonic()-start,2),diagnostic_count=len(diagnostics)))
    state.update(phases=phases);marker.write_text(json.dumps(state,indent=2)+'\n')
    if ret:break
state.update(terminal=True,seconds=round(time.monotonic()-begin,2));marker.write_text(json.dumps(state,indent=2)+'\n')
assert len(phases)==3 and all(p['exit']==0 for p in phases),phases
assert snapshot(payload)==payload_manifest and snapshot(original)==initial
def config_map(text):return {l.split('=',1)[0]:l for l in text.splitlines() if l.startswith('CONFIG_') or l.startswith('# CONFIG_')}
old_config=config_map(before);new_config=config_map((BUILD/'.config').read_text())
changes={k:dict(before=old_config.get(k),after=new_config.get(k)) for k in old_config.keys()|new_config.keys() if old_config.get(k)!=new_config.get(k)}
assert all(k in ['CONFIG_INITRAMFS_SOURCE','CONFIG_INITRAMFS_ROOT_UID','CONFIG_INITRAMFS_ROOT_GID'] or 'CONFIG_INITRAMFS_COMPRESSION_' in k for k in changes),changes
assert new_config['CONFIG_INITRAMFS_ROOT_UID']=='CONFIG_INITRAMFS_ROOT_UID=0'
assert new_config['CONFIG_INITRAMFS_ROOT_GID']=='CONFIG_INITRAMFS_ROOT_GID=0'
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
release=(BUILD/'include/config/kernel.release').read_text().strip()
stage=module_root/'lib/modules'/release
assert stage.is_dir()
for n in ['build','source']:
    link=stage/n
    if link.is_symlink():link.unlink()
modules=list(stage.rglob('*.ko'));assert len(modules)==778
for p in modules:
    assert subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).split()[0]==release
depmod=subprocess.run(['depmod','-e','-F',str(BUILD/'System.map'),'-b',str(module_root),release],capture_output=True)
(PRIVATE/'boot-depmod-private.log').write_bytes(depmod.stdout+depmod.stderr)
assert depmod.returncode==0 and not depmod.stdout and not depmod.stderr
archive=PRIVATE/'modules-pix288-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:tar.add(stage,arcname='usr/lib/modules/'+release)
names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','vmlinux','Module.symvers','modules.order','.config']
artifacts={n:dict(bytes=(BUILD/n).stat().st_size,sha256=sha(BUILD/n)) for n in names}
assert artifacts['arch/arm64/boot/Image']['bytes']<64*1024*1024-1024*1024
assert artifacts['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']=='dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
report=dict(stage=288,commit=COMMIT,terminal=True,phases=phases,seconds=state['seconds'],release=release,
            artifacts=artifacts,embedded_input_entries=len(payload_manifest),boot_scripts_and_auth_match_image183=True,
            embedded_modules_rebuilt=module_changes,original_initramfs_preserved=True,
            configuration_changed_only_initramfs_and_compression=True,root_uid_gid_mapping_zero=True,changed_config_keys=sorted(changes),
            module_count=778,all_installed_vermagic_match=True,depmod_unresolved_symbols=0,
            module_archive=dict(bytes=archive.stat().st_size,sha256=sha(archive)),
            fits_logdump_partition_capacity=True,no_device_write=True,boot_not_yet_verified=True,
            not_deployed=True,hardware_isp_not_yet_verified=True)
(ROOT/'boot-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(PRIVATE/'boot-candidate-result-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
