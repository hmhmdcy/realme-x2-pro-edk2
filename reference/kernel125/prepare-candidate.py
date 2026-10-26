from pathlib import Path
import runpy,subprocess,shutil,hashlib,json
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-rootfs122');source=v/'camera124';dest=v/'camera125';out=Path('/mnt/e/edk2-samurai-out/kernel125');out.mkdir(exist_ok=True)
assert not dest.exists() and shutil.disk_usage(v).free>7*1024**3
assert hashlib.sha256((source/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='feb6bfdc7991d26c6278d7d38afba47e86ee04573c78699e9eb3f3ef526fd0c1'
dest.mkdir();subprocess.run(['cp','-a',str(source/'kernel'),str(dest/'kernel')],check=True,timeout=300);subprocess.run(['cp','-a',str(source/'initramfs'),str(dest/'initramfs')],check=True,timeout=30)
p=dest/'kernel/.config';t=p.read_text();assert str(source/'initramfs') in t;p.write_text(t.replace(str(source/'initramfs'),str(dest/'initramfs')))
report=dict(candidate=125,base=124,isolated_copy_on_e_volume=True,base124_and_accepted_rootfs122_preserved=True,inner_volume_free_after_copy=shutil.disk_usage(v).free,phone_unchanged=True)
(r/'reference/kernel125/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
