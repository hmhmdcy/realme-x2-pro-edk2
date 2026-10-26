from pathlib import Path
import subprocess,runpy,hashlib,json,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126'
runpy.run_path(str(ref/'ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-build126');base=Path('/home/cy122/pmos-samurai-rootfs122/camera125')
assert not (v/'kernel').exists() and shutil.disk_usage(v).free>20*1024**3
assert hashlib.sha256((base/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='4bded2cb151f910adc3ccd7c6545f4f2702b9a3a1022d4b9dbbcd5364edcf389'
for name in ['kernel','initramfs']:subprocess.run(['cp','-a',str(base/name),str(v/name)],check=True,timeout=300)
p=v/'kernel/.config';t=p.read_text();assert str(base/'initramfs') in t;p.write_text(t.replace(str(base/'initramfs'),str(v/'initramfs')))
(ref/'candidate-source-validation.json').write_text(json.dumps(dict(candidate=126,base=125,isolated_new_e_volume=True,source125_preserved=True,accepted_rootfs122_preserved=True,inner_free_bytes_after_copy=shutil.disk_usage(v).free,phone_unchanged=True),indent=2)+'\n');print('K126_SOURCE125_ISOLATED_COPY_VERIFIED')
