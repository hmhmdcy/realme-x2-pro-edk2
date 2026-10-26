from pathlib import Path
import os,stat,hashlib,json,runpy,tarfile,struct,subprocess
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122');out=Path('/mnt/e/edk2-samurai-out/kernel122')
base=Path('/home/cy122/pmos-samurai-rootfs115/rootfs');root=Path('/home/cy122/pmos-samurai-rootfs122/rootfs')
release='7.3.0-rc6-rmx1931-samurai+';modroot=root/'usr/lib/modules'/release
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def manifest(folder):
    result={}
    for parent,dirs,files in os.walk(folder,followlinks=False):
        for name in dirs+files:
            p=Path(parent)/name;relative=p.relative_to(folder).as_posix()
            if relative=='usr/lib/modules' or relative.startswith('usr/lib/modules/') or relative=='etc/samurai-rootfs-stage':continue
            s=p.lstat();item=dict(mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
            if stat.S_ISREG(s.st_mode):item.update(size=s.st_size,sha256=digest(p))
            elif stat.S_ISLNK(s.st_mode):item['target']=os.readlink(p)
            elif stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):item['rdev']=s.st_rdev
            result[relative]=item
    return result
before=manifest(base);after=manifest(root)
assert before==after,'non-module userspace content or metadata differs'
(out/'userspace-manifest-private.json').write_text(json.dumps(after,sort_keys=True)+'\n')
archive=Path('/mnt/e/edk2-samurai-out/kernel121/modules-k121-private.tar.gz')
module_count=0;vermagic=set()
with tarfile.open(archive) as tf:
    for m in tf:
        if not m.isfile():continue
        dest=root/'usr'/m.name;expected=tf.extractfile(m).read()
        # depmod can regenerate index bytes; compare every .ko byte to the
        # validated complete matching archive, then verify regenerated deps.
        if not m.name.endswith('.ko'):continue
        actual=dest.read_bytes();assert actual==expected
        assert actual[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',actual,18)[0]==183
        start=actual.index(b'vermagic=')+9;vermagic.add(actual[start:actual.index(b'\0',start)].decode())
        module_count+=1
assert module_count==770 and len(vermagic)==1 and next(iter(vermagic)).startswith(release+' ')
known={p.relative_to(modroot).as_posix() for p in modroot.rglob('*.ko')}
for line in (modroot/'modules.dep').read_text().splitlines():
    name,deps=line.split(':',1);assert name in known and all(x in known for x in deps.split())
assert not any(p.is_symlink() for p in modroot.rglob('*'))
mapfile=Path('/home/cy122/pmos-samurai-kernel118/camera121/kernel/System.map')
result=subprocess.run(['depmod','-e','-F',str(mapfile),'-b',str(root),release],capture_output=True,text=True,timeout=30)
(out/'stage-depmod-check-private.txt').write_text(result.stdout+result.stderr);assert result.returncode==0 and result.stdout+result.stderr==''
count=sum(line.startswith('P:') for line in (root/'lib/apk/db/installed').read_text().splitlines());assert count==936
assert (root/'lib').is_symlink() and os.readlink(root/'lib')=='usr/lib'
for service in ['elogind','postmarketos-zram-swap']:subprocess.run(['sh','-n',str(root/'etc/init.d'/service)],check=True)
report=dict(candidate_kernel=121,rootfs_stage=122,userspace_packages=count,userspace_manifest_entries=len(before),all_non_module_userspace_content_metadata_identical=True,apk_world_and_database_preserved=True,firmware_credentials_and_services_preserved=True,all_770_modules_exactly_match_validated121_archive=True,all_modules_aarch64_elf64=True,single_matching_vermagic=True,all_module_dependencies_present=True,depmod_system_map_no_diagnostics=True,no_module_symlinks=True,root_lib_symlink_correct=True,full_hardware_acceptance=False,no_phone_changes=True,goal_complete=False)
(ref/'rootfs-content-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
