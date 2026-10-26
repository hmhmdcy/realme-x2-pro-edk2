from pathlib import Path
import json,hashlib,subprocess,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');build=json.loads((ref/'kernel-build-validation.json').read_text());base=Path('/mnt/e/edk2-samurai-out/kernel115')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
boot=base/'boot-partition-k115.img';fat=base/'logdump-k115-ipa-zram.img'
assert boot.stat().st_size==100663296 and sha(boot)=='e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f'
assert fat.stat().st_size==67108864 and sha(fat)=='fcb1b5380e664a49abf7d6098863d23683f70be4c1d1d144df5a8dd356e46e2e'
target=out/'logdump-k126-internal-tpg.img';bootcopy=out/'boot-partition-k126-uefi-reused.img'
if target.exists():
 previous=json.loads((ref/'boot-package-validation.json').read_text());assert previous['not_deployed'] and sha(target)==previous['logdump_sha256']
 backup=out/'logdump-k126-before-bt-private.img';assert not backup.exists();target.rename(backup)
 assert bootcopy.exists() and sha(bootcopy)==sha(boot)
else:
 assert not bootcopy.exists();shutil.copyfile(boot,bootcopy)
shutil.copyfile(fat,target)
for name,dest in [('Image','Image'),('DTB','samurai.dtb')]:
 source=out/(name+'-k126-private');assert sha(source)==next(a['sha256'] for a in build['artifacts'] if a['role']==name)
 subprocess.run(['mcopy','-o','-i',str(target),str(source),'::/'+dest],check=True)
 assert subprocess.check_output(['mcopy','-i',str(target),'::/'+dest,'-'])==source.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
cp=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);(out/'logdump-fat-check-private.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0
report=dict(candidate=126,release=build['release'],uefi_boot115_reused_byte_exact=True,boot_sha256=sha(bootcopy),boot_bytes=bootcopy.stat().st_size,logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,fat_readback_exact=True,fat_readonly_check_pass=True,fat_only_image_and_dtb=True,camss_enabled_for_internal_tpg=True,cci_and_external_sensors_disabled=True,old118_modules_preserved_via_distinct_release=True,flash_partitions=['logdump'],not_deployed=True,current_boot_full_guard_required=True,goal_complete=False)
(ref/'boot-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'boot-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
