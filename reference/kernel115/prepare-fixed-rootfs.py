from pathlib import Path
import hashlib,json,subprocess,shutil
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
root=Path('/home/cy122/pmos-samurai-rootfs115/rootfs')
baseline=json.loads((out/'rootfs-image-validation.json').read_text())
assert baseline['both_fsck_pass'] and baseline['sparse_reconstruction_matches']
fixed=out/'ipa-delay-fixed.ko'
assert hashlib.sha256(fixed.read_bytes()).hexdigest()=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
shutil.copyfile(fixed,root/'usr/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko')
subprocess.run(['depmod','-b',str(root),'7.3.0-rc6-rmx1931-samurai+'],check=True)
for name in ['pack-rootfs.sh','verify-sparse.py','finalize-rootfs.py']:
    t=(ref/name).read_text()
    t=t.replace('samurai-rootfs-f2fs-final.raw.img','samurai-rootfs-f2fs-delay-fixed.raw.img').replace('samurai-rootfs-f2fs-restored.raw.img','samurai-rootfs-f2fs-delay-fixed-restored.raw.img').replace('samurai-rootfs-f2fs.simg','samurai-rootfs-f2fs-delay-fixed.simg')
    t=t.replace('fsck-raw-private.log','fsck-fixed-raw-private.log').replace('fsck-restored-private.log','fsck-fixed-restored-private.log').replace('mkfs-private.log','mkfs-fixed-private.log').replace('sload-private.log','sload-fixed-private.log').replace('sparse-check.log','sparse-fixed-check.log')
    t=t.replace('sparse-validation.json','sparse-fixed-validation.json').replace('rootfs-image-validation.json','rootfs-fixed-image-validation.json').replace('rootfs.sha256','rootfs-fixed.sha256')
    t=t.replace('verify-sparse.py','verify-sparse-fixed.py').replace('finalize-rootfs.py','finalize-rootfs-fixed.py')
    t=t.replace('final_coreutils_hash_allocation_failure_recovered_with_bounded_python_stream=True','tx_delay_register_fix_included=True')
    dest=ref/name.replace('.py','-fixed.py').replace('.sh','-fixed.sh')
    dest.write_text(t)
print('ROOTFS115B_MATCHING_TX_DELAY_MODULE_AND_BASELINE_IMAGE_PRESERVED')
