from pathlib import Path
import hashlib
import json
import shutil
import gzip

kernel=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel74')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel74')
previous=out.parent/'kernel73'
for name, src in {
    'Image-before':kernel/'arch/arm64/boot/Image',
    'config-before':kernel/'.config',
    'dtb-before':kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
    'logdump-before.img':previous/'logdump-k73-display-deps.img',
    'boot-before.img':previous/'boot-k73-display.img',
}.items():
    assert not (out/name).exists(),name
    shutil.copyfile(src,out/name)
core=['drivers/tty/serial/eud.c','drivers/tty/serial/eud_earlycon.c',
      'drivers/input/rmi4/rmi_i2c.c','drivers/soc/qcom/rpmh.c',
      'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
      'drivers/gpu/drm/panel/panel-samsung-sofef03f.c']
display=['drivers/gpu/drm/msm/disp/dpu1/'+n for n in
    ('dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_hw_intf.c','dpu_hw_intf.h')]
hashes={n:hashlib.sha256((kernel/n).read_bytes()).hexdigest() for n in core+display}
for n in display:
    shutil.copyfile(kernel/n,out/(Path(n).name+'.before'))
hashes['init']=hashlib.sha256(Path('/home/cy122/x2pro-linux/initramfs/init').read_bytes()).hexdigest()
hashes['samurai-usb']=hashlib.sha256(Path('/home/cy122/x2pro-linux/initramfs/usr/sbin/samurai-usb').read_bytes()).hexdigest()
(ref/'sources-before.json').write_text(json.dumps(hashes,indent=2)+'\n')
raw=gzip.decompress((out/'before-dmesg.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest()=='e4f6b522d8982d6cb891e4929a19bff2b377d1b3adb5316af3f4500edd9d851e'
(ref/'before-dmesg.txt').write_bytes(raw)
shutil.copyfile(out/'before-dmesg.gz',ref/'before-dmesg.gz')
print(json.dumps(hashes,indent=2))
