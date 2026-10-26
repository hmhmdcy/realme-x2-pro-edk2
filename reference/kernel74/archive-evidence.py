from pathlib import Path
import gzip
import hashlib
import json
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
dest = root/'reference/kernel74'
out = Path('/mnt/e/edk2-samurai-out/kernel74')
kernel = Path('/home/cy122/x2pro-linux/linux')
sha = lambda data: hashlib.sha256(data).hexdigest()

receipts = json.loads((dest/'capture-receipts.json').read_text())
records = {}
for name, expected in receipts.items():
    compressed = (out/(name+'.gz')).read_bytes()
    raw = gzip.decompress(compressed)
    assert sha(raw) == expected['raw_sha256'], name
    assert sha(compressed) == expected['gzip_sha256'], name
    (dest/(name+'.gz')).write_bytes(compressed)
    (dest/(name+'.txt')).write_bytes(raw)
    records[name] = dict(**expected, raw_bytes=len(raw), gzip_bytes=len(compressed),
                         device_sha256_matches=True, gzip_crc_pass=True)
(dest/'capture-validation.json').write_text(json.dumps(records,indent=2)+'\n')
for source in out.iterdir():
    if source.suffix in ('.json','.jsonl','.txt','.raw','.usbmon','.log','.out','.err'):
        assert source.stat().st_size < 2*1024*1024, source
        shutil.copyfile(source,dest/source.name)
changes = ['dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_hw_intf.c','dpu_hw_intf.h']
before = json.loads((dest/'sources-before.json').read_text())
preserved = {}
for name, expected in before.items():
    if Path(name).name in changes:
        assert sha((out/(Path(name).name+'.before')).read_bytes()) == expected
        shutil.copyfile(out/(Path(name).name+'.before'),dest/(Path(name).name+'.before'))
        shutil.copyfile(kernel/name,dest/(Path(name).name+'.after'))
        continue
    actual = (Path('/home/cy122/x2pro-linux/initramfs/init') if name=='init' else
              Path('/home/cy122/x2pro-linux/initramfs/usr/sbin/samurai-usb') if name=='samurai-usb' else kernel/name)
    assert sha(actual.read_bytes()) == expected, name
    preserved[name] = expected
shutil.copyfile(out/'config-before',dest/'config-before')
assert (out/'config-before').read_bytes() == (kernel/'.config').read_bytes()
assert (out/'dtb-before').read_bytes() == (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
patch = dest/'handoff-drain.patch'
shutil.copyfile(patch,root/'linux-port/patches/0010-drm-msm-sm8150-command-boot-handoff.patch')
(dest/'core-preservation.json').write_text(json.dumps(dict(unchanged=preserved,
    config_unchanged=True, dtb_unchanged=True,
    config_sha256=sha((kernel/'.config').read_bytes()),
    dtb_sha256=sha((out/'dtb-before').read_bytes())),indent=2)+'\n')
shutil.copyfile(out/'dpu_hw_ctl.c.with-start',dest/'dpu_hw_ctl.c.with-start')
print(f'Archived {len(records)} device captures and seven-file kernel delta; preserved {len(preserved)} core sources.')
