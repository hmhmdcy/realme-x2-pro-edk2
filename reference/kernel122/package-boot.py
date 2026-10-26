from pathlib import Path
import json,hashlib,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122')
base=Path('/mnt/e/edk2-samurai-out/kernel115');candidate=Path('/mnt/e/edk2-samurai-out/kernel121')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
boot=base/'boot-partition-k115.img';fat=base/'logdump-k115-ipa-zram.img';image=candidate/'Image-k121-private';dtb=candidate/'sm8150-samurai-k121-private.dtb'
assert boot.stat().st_size==100663296 and sha(boot)=='e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f'
assert fat.stat().st_size==67108864 and sha(fat)=='fcb1b5380e664a49abf7d6098863d23683f70be4c1d1d144df5a8dd356e46e2e'
assert sha(image)=='46a49619786e11cbb230da8a4aea204c5ee0ab3d743c4c9846c297e9ecb2c0c8'
assert sha(dtb)=='31a9f7f0e49d22b5ea5173a5f4916c176ecd7f9e610fef5649a702c1c08e4548'
target=out/'logdump-k121-camera-basis.img';bootcopy=out/'boot-partition-k121-uefi-reused.img'
assert not target.exists() and not bootcopy.exists()
shutil.copyfile(fat,target);shutil.copyfile(boot,bootcopy)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
subprocess.run(['mcopy','-o','-i',str(target),str(dtb),'::/samurai.dtb'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
p=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);(out/'logdump-fat-check-private.txt').write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert sha(bootcopy)==sha(boot)
report=dict(candidate_kernel=121,uefi_boot_115_reused_byte_exact=True,boot_image_bytes=bootcopy.stat().st_size,boot_sha256=sha(bootcopy),logdump_bytes=target.stat().st_size,logdump_sha256=sha(target),image_sha256=sha(image),dtb_sha256=sha(dtb),fat_contents_only_image_and_dtb=True,fat_readback_exact=True,fat_readonly_check_pass=True,new_cci_nodes_disabled=True,no_pmic_or_sensor_nodes_enabled=True,matching_full_rootfs_still_building=True,not_deployed=True,fresh_current_boot_flywheel_audit_required_before_deploy=True,goal_complete=False)
(ref/'boot-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
