from pathlib import Path
import runpy,subprocess,shutil,hashlib,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
mount=Path('/home/cy122/pmos-samurai-kernel118');source=mount/'camera120';dest=mount/'camera121'
out=Path('/mnt/e/edk2-samurai-out/kernel121');out.mkdir(exist_ok=True)
assert not dest.exists() and shutil.disk_usage(mount).free>7*1024**3
assert hashlib.sha256((source/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='0ec2560bdb332ead8a0bea7636f4fd3d80e041f7ac370f71d20e1f80df183bf9'
dest.mkdir()
subprocess.run(['cp','-a',str(source/'kernel'),str(dest/'kernel')],check=True,timeout=240)
subprocess.run(['cp','-a',str(source/'initramfs'),str(dest/'initramfs')],check=True,timeout=30)
p=dest/'kernel/.config';before=p.read_text();assert str(source/'initramfs') in before;p.write_text(before.replace(str(source/'initramfs'),str(dest/'initramfs')))
report=dict(candidate=121,base=120,isolated_copy_on_e_volume=True,baseline120_image_preserved=True,phone_unchanged=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
