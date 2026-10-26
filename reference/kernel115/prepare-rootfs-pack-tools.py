from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
ref=root/'kernel115'
for name in ['pack-rootfs.sh','verify-sparse.py','finalize-rootfs.py']:
    t=(root/'kernel114'/name).read_text().replace('rootfs114','rootfs115').replace('kernel114','kernel115')
    t=t.replace('rootfs115-current-hardware-kernel113','rootfs115-ipa-zram-kernel115')
    t=t.replace('compatible_running_kernel=113','compatible_running_kernel=115')
    t=t.replace('test -f "$out/userspace-complete.json"','test -f "$out/rootfs-stage-validation.json"')
    (ref/name).write_text(t)
print('ROOTFS115_PACK_AND_BOUNDED_SPARSE_RECONSTRUCTION_TOOLS_READY')
