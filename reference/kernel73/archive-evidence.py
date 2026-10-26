from pathlib import Path
import difflib
import gzip
import hashlib
import json
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel73')
dest = root/'reference/kernel73'
kernel = Path('/home/cy122/x2pro-linux/linux')
sha = lambda data: hashlib.sha256(data).hexdigest()
device_raw = {
    'before-dmesg': '28f9c085c4a47c8623e3aa503121ea596acfda7a801e12740e418a6eb6a333fd',
    'first-dmesg': '71cffddfaf551fa8ee504cc239f073c4faf3519b144134909da857f516d48c0a',
    'reprobe-dmesg': 'cfa427fd98334e7776c7a3b97221c35a5feb0a96b7784ba0f44cf6e1747eb03a',
    'deps-dmesg': 'c1fa78bf869d33b5157a415786fa2e10204c7cca4dabef64fc5ea41a7111a12a',
    'tested-dmesg': 'b6c4d1066dfbabd265b5fdd2efc4444d196c7095e88f8fd97c5d7f158de5aad1',
    'cycled-dmesg': '4de74e0073c1b9ad649d5dd2db653b29c14c0c1340ccd715e21a12b811b9df73',
    'cycled-facts': '9d5c702bfb936fe7fa54e9870f910d3ce643fc7ca636f9bff9851c8745dfbb7a',
    'reboot-dmesg': '1ecf3ffe939b4217b37154945902188ba592ff24b0d77715f5e8056169cbb29d',
    'final-dmesg': '4c35ab03e37c91532eb7346314daa2a76cac3b6e8e5bfb4922e6e458047bf386',
    'final-facts': 'a691e169a919660be6b437e61a5851c643ef16d05dae8d082916be345f138c75',
}
records = {}
for name, expected in device_raw.items():
    compressed = (out/(name+'.gz')).read_bytes()
    raw = gzip.decompress(compressed)  # Validates gzip CRC and ISIZE.
    assert sha(raw) == expected, name
    (dest/(name+'.gz')).write_bytes(compressed)
    (dest/(name+'.txt')).write_bytes(raw)
    records[name] = dict(raw_sha256=expected, raw_bytes=len(raw),
                         gzip_sha256=sha(compressed), gzip_bytes=len(compressed),
                         device_sha256_matches=True, gzip_crc_pass=True)
(dest/'capture-validation.json').write_text(json.dumps(records,indent=2)+'\n')
excluded = ('gpu-firmware-stock.tar', 'kms-smoke')
for source in out.iterdir():
    if source.name in excluded or source.suffix in ('.img','.fd','.Fv','.gz') or source.name.startswith('Image'):
        continue
    if source.suffix in ('.json','.jsonl','.txt','.raw','.usbmon','.log','.out','.err','.sha256'):
        assert source.stat().st_size < 2*1024*1024, source
        shutil.copyfile(source,dest/source.name)
for name in ('config-before','config-display-deps','dts-before','panel-kconfig-before','panel-makefile-before'):
    shutil.copyfile(out/name,dest/name)
for name in ('firmware-before.dtb','firmware-after.dtb'):
    shutil.copyfile(out/name,dest/name)
shutil.copyfile(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',root/'linux-port/dts/sm8150-samurai.dts')
shutil.copyfile(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',dest/'dts-after')
# Incremental patch starts from the verified session72 source; retain older EUD/RMI fixes.
changes = [
    ('arch/arm64/boot/dts/qcom/sm8150-samurai.dts',out/'dts-before'),
    ('drivers/gpu/drm/panel/Kconfig',out/'panel-kconfig-before'),
    ('drivers/gpu/drm/panel/Makefile',out/'panel-makefile-before'),
    ('drivers/gpu/drm/panel/panel-samsung-sofef03f.c',None),
    ('Documentation/devicetree/bindings/display/panel/samsung,sofef03f-m.yaml',None),
]
patch = []
for name, before in changes:
    old = before.read_text().splitlines(keepends=True) if before else []
    new = (kernel/name).read_text().splitlines(keepends=True)
    patch.extend(difflib.unified_diff(old,new,fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(root/'linux-port/patches/0009-drm-panel-samsung-sofef03f-native-display.patch').write_text(''.join(patch))
before_config = dict(line.split('=',1) for line in (out/'config-before').read_text().splitlines() if line.startswith('CONFIG_'))
fragment = ['# Native display session73, against the running session72 configuration.\n']
for line in (out/'config-display-deps').read_text().splitlines():
    if line.startswith('CONFIG_') and before_config.get(line.split('=',1)[0]) != line.split('=',1)[1]:
        fragment.append(line+'\n')
    elif line.startswith('# CONFIG_') and line.split()[1] in before_config:
        fragment.append(line+'\n')
(root/'linux-port/kernel73-builtins.config').write_text(''.join(fragment))
preserved = json.loads((dest/'core-before.json').read_text())
for name, expected in preserved.items():
    assert sha((kernel/name).read_bytes()) == expected, name
assert Path('/home/cy122/x2pro-linux/initramfs/init').read_bytes() == (root/'linux-port/initramfs/init').read_bytes()
assert Path('/home/cy122/x2pro-linux/initramfs/usr/sbin/samurai-usb').read_bytes() == (root/'linux-port/scripts/samurai-usb.sh').read_bytes()
(dest/'core-preservation.json').write_text(json.dumps(dict(unchanged=preserved,
    rpmh_current_sha256=sha((kernel/'drivers/soc/qcom/rpmh.c').read_bytes()),
    init_current_sha256=sha(Path('/home/cy122/x2pro-linux/initramfs/init').read_bytes()),
    usb_current_sha256=sha(Path('/home/cy122/x2pro-linux/initramfs/usr/sbin/samurai-usb').read_bytes())),indent=2)+'\n')
print(json.dumps(records,indent=2))
