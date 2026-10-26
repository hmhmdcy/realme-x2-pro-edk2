from pathlib import Path
import hashlib,json,os,runpy,shutil,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel128')
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
base=Path('/home/cy122/pmos-samurai-build126');stage=Path('/home/cy122/pmos-samurai-kernel128')
assert os.geteuid()==0 and not stage.exists()
assert hashlib.sha256((base/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='d2b2c7e24c792be752c3b6db96ee02e4b745fd2255bab0a2d3c46483ddd20181'
assert hashlib.sha256((base/'kernel/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()).hexdigest()=='166384b8994883ccb31220fc18c7a94f1f9dcdb8fc2244a4375d7f74d1a4e475'
stage.mkdir(mode=0o700)
for name in ['kernel','initramfs']:
 subprocess.run(['cp','-a',str(base/name),str(stage/name)],check=True,timeout=300)
source=base/'kernel/.config';target=stage/'kernel/.config';text=target.read_text();assert text==source.read_text()
assert text.count('CONFIG_LOCALVERSION="-rmx1931-samurai-k126"')==1 and text.count(str(base/'initramfs'))==1
target.write_text(text.replace('CONFIG_LOCALVERSION="-rmx1931-samurai-k126"','CONFIG_LOCALVERSION="-rmx1931-samurai-k128"').replace(str(base/'initramfs'),str(stage/'initramfs')))
original=base/'kernel/drivers/net/wireless/ath/ath10k/mac.c';candidate=stage/'kernel/drivers/net/wireless/ath/ath10k/mac.c'
assert original.read_bytes()==candidate.read_bytes()
(out/'original126-ath10k-mac-private.c').write_bytes(original.read_bytes())
report=dict(candidate=128,base=126,isolated_c_wsl_copy=True,source126_preserved=True,stable126_image_and_embedded_dtb_verified=True,localversion_and_initramfs_path_changed_only=True,driver_patch_pending=True,phone_unchanged=True)
(r/'reference/kernel128/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K128_SOURCE126_ISOLATED_C_WSL_COPY_READY_PATCH_PENDING',flush=True)
