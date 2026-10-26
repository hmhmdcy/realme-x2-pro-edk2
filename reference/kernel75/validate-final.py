from pathlib import Path
import hashlib, json, subprocess, runpy

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel75')
kernel = Path('/home/cy122/x2pro-linux/linux')
initramfs = Path('/home/cy122/x2pro-linux/initramfs')
sha = lambda data: hashlib.sha256(data).hexdigest()
before = json.loads((ref/'sources-before.json').read_text())
unchanged = {}
for n in ('drivers/tty/serial/eud.c','drivers/tty/serial/eud_earlycon.c',
          'drivers/input/rmi4/rmi_i2c.c','drivers/soc/qcom/rpmh.c',
          'drivers/gpu/drm/msm/disp/dpu1/dpu_rm.h',
          'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.h','init','samurai-usb'):
    p = initramfs/('init' if n=='init' else 'usr/sbin/samurai-usb') if n in ('init','samurai-usb') else kernel/n
    unchanged[n] = sha(p.read_bytes())
    assert unchanged[n] == before[n], n
assert (kernel/'.config').read_bytes() == (out/'config-before').read_bytes()
assert (kernel/'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_dsc.c').read_bytes() == (out/'dpu_hw_dsc.c.before').read_bytes()
assert (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes() == (out/'firmware-after.dtb').read_bytes()
assert (kernel/'arch/arm64/boot/Image').read_bytes() == (out/'Image-final').read_bytes()
assert subprocess.check_output(['mcopy','-i',str(out/'logdump-k75-final.img'),'::Image','-']) == (out/'Image-final').read_bytes()
cpio = runpy.run_path(str(ref/'validate-initramfs.py'))['files']
firmware = json.loads((ref/'gpu-installed-manifest.json').read_text())
for n, item in firmware.items():
    assert sha(cpio['lib/firmware/'+n]['body']) == item['sha256'], n
subprocess.run(['python3',str(ref/'verify-firmware.py')],check=True,stdout=(out/'final-firmware-audit.txt').open('w'))
assert '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0' in (out/'final-device-readback.txt').read_text()
assert '43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b' in (out/'final-device-readback.txt').read_text()
historical = {}
for line in (ref.parent/'kernel74/SHA256SUMS').read_text().splitlines():
    expected, n = line.split('  ',1)
    actual = sha((ref.parent/'kernel74'/n).read_bytes())
    if expected != actual:
        historical[n] = {'expected':expected,'actual':actual}
assert not historical, historical
artifacts = {n:dict(bytes=(out/n).stat().st_size,sha256=sha((out/n).read_bytes())) for n in (
    'Image-final','logdump-k75-final.img','boot-k75-gpu.img','firmware-after.dtb','config-before',
    'logdump-before.img','boot-before.img')}
report = dict(preserved_sources=unchanged,config_unchanged=True,
              removed_dsc_diagnostics=True,firmware_cpio_verified=True,
              firmware_android_fv_ffs_pass=True,device_partition_readback_pass=True,
              historical_kernel74_seal_pass=True,artifacts=artifacts)
(out/'final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: source preservation, config/DTB, FAT Image, CPIO/firmware, UEFI, device readback, historical evidence seal.')
