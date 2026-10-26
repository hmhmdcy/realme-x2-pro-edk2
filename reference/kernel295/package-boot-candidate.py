"""Verify the actual embedded payload and package the FAT image without a device write."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,tarfile,zlib

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel295')
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
report=json.loads((ROOT/'boot-candidate-build-validation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
image=BUILD/'arch/arm64/boot/Image';dtb=BUILD/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert sha(image)==report['artifacts']['arch/arm64/boot/Image']['sha256']
assert sha(dtb)==report['artifacts']['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']
raw=image.read_bytes();archives=[]
for match in re.finditer(b'\x1f\x8b\x08',raw):
    try:
        dec=zlib.decompressobj(16+zlib.MAX_WBITS);data=dec.decompress(raw[match.start():],64*1024*1024)
        if data.startswith((b'070701',b'070702')) and b'TRAILER!!!' in data:archives.append(data)
    except zlib.error:pass
assert len(archives)==1
b=archives[0];pos=0;files={}
while pos+110<=len(b):
    h=b[pos:pos+110];assert h[:6] in [b'070701',b'070702']
    values=[int(h[6+i*8:14+i*8],16) for i in range(13)]
    size,namesize=values[6],values[11];name=b[pos+110:pos+110+namesize-1].decode().removeprefix('./')
    start=(pos+110+namesize+3)&~3
    if name=='TRAILER!!!':break
    files[name]=b[start:start+size];pos=(start+size+3)&~3
payload=BUILD.parent/'input-initramfs295'
required=['init','usr/sbin/samurai-rootfs','usr/sbin/samurai-usb','etc/dropbear/dropbear_ed25519_host_key','root/.ssh/authorized_keys']+report['embedded_modules_rebuilt']
for name in required:assert files[name]==(payload/name).read_bytes(),name
assert b'switch_root' in files['usr/sbin/samurai-rootfs'] and b'diagnostic fallback' in files['usr/sbin/samurai-rootfs']
archive=PRIVATE/'modules-k295-private.tar.gz'
assert sha(archive)==report['module_archive']['sha256']
with tarfile.open(archive) as tar:
    members=tar.getmembers();prefix='usr/lib/modules/'+report['release']
    assert all(m.name==prefix or m.name.startswith(prefix+'/') for m in members)
    assert all('..' not in Path(m.name).parts and not m.issym() and not m.islnk() for m in members)
    assert sum(m.name.endswith('.ko') for m in members)==778
rollback=PRIVATE.parent/'kernel290/logdump-k290-candidate-private.img'
boot=PRIVATE.parent/'kernel276/boot-partition-k276-cci-io.img'
assert sha(rollback)=='0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a'
assert sha(boot)=='0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64'
target=PRIVATE/'logdump-k295-candidate-private.img'
saved=PRIVATE/'Image-k295-private'
assert not target.exists() and not saved.exists()
shutil.copyfile(image,saved);shutil.copyfile(rollback,target)
for source,name in [(saved,'Image'),(dtb,'samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(source),'::/'+name],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),'::/'+name,'-'])==source.read_bytes()
check=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(PRIVATE/'candidate-fat-check-private.log').write_bytes(check.stdout+check.stderr)
assert check.returncode==0
out=dict(stage=295,commit=report['commit'],release=report['release'],kernel_build=295,
         image_sha256=sha(saved),image_bytes=saved.stat().st_size,
         logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
         dtb_sha256=sha(dtb),firmware_boot_preserved_sha256=sha(boot),rollback_logdump_sha256=sha(rollback),
         original_boot_and_logdump_verified=True,actual_image_embedded_cpio_verified=True,
         boot_and_recovery_scripts_and_auth_verified=True,all_three_embedded_modules_match_installed_tree=True,
         module_archive_safe_paths_and_778_modules_verified=True,module_archive=report['module_archive'],
         fat_image_and_dtb_readback_exact=True,fat_readonly_check_pass=True,
         planned_flash_partitions=['logdump'],no_device_write=True,not_deployed=True,
         hardware_isp_not_yet_verified=True)
(ROOT/'boot-package-validation.json').write_text(json.dumps(out,indent=2)+'\n')
(PRIVATE/'boot-package-validation-private.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
