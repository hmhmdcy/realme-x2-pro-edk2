from pathlib import Path
import runpy,os,stat,subprocess,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122');out=Path('/mnt/e/edk2-samurai-out/kernel122')
fixture=stage/'device-fixture';assert not fixture.exists();fixture.mkdir(mode=0o700)
source=fixture/'source';source.mkdir();export=fixture/'export';image=fixture/'fixture-f2fs.img'
for name,kind,maj,min in [('null',stat.S_IFCHR,1,3),('wide-char',stat.S_IFCHR,511,65535),('wide-block',stat.S_IFBLK,259,1025)]:os.mknod(source/name,kind|0o640,os.makedev(maj,min))
for name,mode in [('setuid',0o4755),('setgid',0o2750)]:
    p=source/name;p.write_bytes(b'F2FS_PERMISSION_AND_DEVICE_FIXTURE\n');os.chown(p,1001,1002);os.chmod(p,mode)
os.symlink('setuid',source/'link')
with image.open('xb') as f:f.truncate(512*1024**2)
install=stage/'tools/install-root';env=dict(os.environ,LD_LIBRARY_PATH=str(install/'usr/local/lib'))
with (out/'device-fixture-private.txt').open('w') as log:
    subprocess.run(['mkfs.f2fs','-f','-t','0',str(image)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    subprocess.run([str(install/'usr/local/sbin/sload.f2fs'),'-P','-f',str(source),str(image)],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=30)
    subprocess.run(['fsck.f2fs','--dry-run',str(image)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    loop=subprocess.check_output(['losetup','--find','--show','--read-only',str(image)],text=True).strip()
    try:
        assert subprocess.check_output(['blockdev','--getro',loop],text=True).strip()=='1'
        subprocess.run([str(install/'usr/local/sbin/dump.f2fs'),'-r','-f','-P','-L','-o',str(export),loop],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=30)
    finally:subprocess.run(['losetup','-d',loop],check=True)
namespace={};text=(ref/'verify-image-export.py').read_text();exec(compile(text[:text.index('expected=manifest(root)')],'shared-image-manifest-functions','exec'),namespace)
expected=namespace['manifest'](source);actual=namespace['manifest'](export);assert expected==actual
report=dict(actual_f2fs_format_load_fsck_readonly_export_pass=True,character_nodes=2,block_nodes=1,large_device_major_minor_roundtrip=True,setuid_setgid_ownership_roundtrip=True,symlink_roundtrip=True,fixture_entries=len(expected),all_content_mode_uid_gid_rdev_xattrs_equal=True,no_phone_use=True)
(ref/'device-fixture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
