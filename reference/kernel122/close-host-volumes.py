from pathlib import Path
import subprocess,runpy,json,shutil
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
root_mount=Path('/home/cy122/pmos-samurai-rootfs122');kernel_mount=Path('/home/cy122/pmos-samurai-kernel118');out=Path('/mnt/e/edk2-samurai-out/kernel122')
roots=[(root_mount,Path('/mnt/e/edk2-samurai-out/kernel122/rootfs-build-volume.ext4'),'rootfs')]
if kernel_mount.is_mount():roots.append((kernel_mount,Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4'),'kernel'))
results=[]
for mount,image,label in roots:
    subprocess.run(['sync','-f',str(mount)],check=True,timeout=30)
    subprocess.run(['umount',str(mount)],check=True,timeout=30);assert not mount.is_mount()
    with (out/(label+'-volume-offline-readonly-fsck.txt')).open('w') as log:
        p=subprocess.run(['e2fsck','-f','-n',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
    results.append(dict(volume=label,unmounted=True,offline_readonly_fsck_exit=p.returncode));assert p.returncode==0
report=dict(volumes=results,only_new_private_e_volumes_checked=True,original_wsl_vhd_not_fscked_or_resized=True,rootfs122_unmounted=True,kernel118_volume_mounted=kernel_mount.is_mount(),host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,goal_complete=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/host-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
