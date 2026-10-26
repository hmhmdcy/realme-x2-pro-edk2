from pathlib import Path
import runpy,subprocess,shutil,hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
mount=Path('/home/cy122/pmos-samurai-rootfs122');source=mount/'camera123';dest=mount/'camera124'
out=Path('/mnt/e/edk2-samurai-out/kernel124');out.mkdir(exist_ok=True)
assert not dest.exists() and shutil.disk_usage(mount).free>7*1024**3
assert hashlib.sha256((source/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='2212b4fb88bca8049732fc9cb0ef80a8b50a0e9a5d786eac5a0bcefb2ce0d6ba'
dest.mkdir()
subprocess.run(['cp','-a',str(source/'kernel'),str(dest/'kernel')],check=True,timeout=300)
subprocess.run(['cp','-a',str(source/'initramfs'),str(dest/'initramfs')],check=True,timeout=30)
p=dest/'kernel/.config';before=p.read_text();assert str(source/'initramfs') in before;p.write_text(before.replace(str(source/'initramfs'),str(dest/'initramfs')))
report=dict(candidate=124,base=123,isolated_copy_on_e_volume=True,baseline123_and_accepted_rootfs122_preserved=True,phone_unchanged=True)
(root/'reference/kernel124/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
