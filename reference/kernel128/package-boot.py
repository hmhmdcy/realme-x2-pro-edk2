from pathlib import Path
import hashlib,json,shutil,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
build=json.loads((ref/'kernel-build-validation.json').read_text());assert build['full_image_modules_dtb_build_pass'] and build['dtb_byte_identical126']
boot=out/'boot-partition-before-private.img';fat=out/'logdump-before-private.img';target=out/'logdump-k128-key-delete.img'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not target.exists() and sha(boot)=='d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8'
assert sha(fat)=='5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2'
shutil.copyfile(fat,target)
for role,dest in [('Image','Image'),('DTB','samurai.dtb')]:
 source=out/f'{role}-k128-private';assert sha(source)==next(x['sha256'] for x in build['artifacts'] if x['role']==role)
 subprocess.run(['mcopy','-o','-i',str(target),str(source),'::/'+dest],check=True)
 assert subprocess.check_output(['mcopy','-i',str(target),'::/'+dest,'-'])==source.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
check=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);assert check.returncode==0
(out/'fat-check-private.txt').write_bytes(check.stdout+check.stderr)
report=dict(candidate=128,release=build['release'],boot126_embedded_dtb_reused_byte_exact=True,
 boot_sha256=sha(boot),boot_bytes=boot.stat().st_size,logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
 fat_readback_exact=True,fat_readonly_check_pass=True,fat_only_image_and_dtb=True,dtb_byte_identical126=True,
 flash_partitions=['logdump'],not_deployed=True,goal_complete=False)
for folder in [ref,out]:(folder/'boot-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
