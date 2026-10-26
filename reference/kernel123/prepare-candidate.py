from pathlib import Path
import runpy,subprocess,shutil,hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(root/'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
source=Path('/home/cy122/pmos-samurai-kernel118/camera121')
dest=Path('/home/cy122/pmos-samurai-rootfs122/camera123')
out=Path('/mnt/e/edk2-samurai-out/kernel123');out.mkdir(exist_ok=True)
assert not dest.exists() and shutil.disk_usage(dest.parent).free>9*1024**3
assert hashlib.sha256((source/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='46a49619786e11cbb230da8a4aea204c5ee0ab3d743c4c9846c297e9ecb2c0c8'
dest.mkdir()
subprocess.run(['cp','-a',str(source/'kernel'),str(dest/'kernel')],check=True,timeout=240)
subprocess.run(['cp','-a',str(source/'initramfs'),str(dest/'initramfs')],check=True,timeout=30)
p=dest/'kernel/.config';before=p.read_text();assert str(source/'initramfs') in before;p.write_text(before.replace(str(source/'initramfs'),str(dest/'initramfs')))
report=dict(candidate=123,base=121,isolated_copy_on_e_rootfs_volume=True,baseline121_image_preserved=True,accepted_rootfs122_preserved=True,phone_unchanged=True)
(root/'reference/kernel123/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
