from pathlib import Path
import hashlib, json, shutil

baseline = Path('/home/cy122/pmos-samurai-kernel111')
stage = Path('/home/cy122/pmos-samurai-kernel112')
out = Path('/mnt/e/edk2-samurai-out/kernel112')
assert not stage.exists() and not out.exists()
out.mkdir(parents=True)
stage.mkdir()
for name in ['kernel', 'initramfs']:
    shutil.copytree(baseline/name, stage/name, symlinks=True)
config = stage/'kernel/.config'
before = config.read_text()
assert 'CONFIG_LOG_BUF_SHIFT=17\n' in before
after = before.replace('/home/cy122/pmos-samurai-kernel111/initramfs', str(stage/'initramfs'))
after = after.replace('CONFIG_LOG_BUF_SHIFT=17\n', 'CONFIG_LOG_BUF_SHIFT=20\n')
config.write_text(after)
(out/'config-before').write_text(before)
helper = stage/'initramfs/usr/sbin/samurai-rootfs'
original = helper.read_bytes()
text = original.decode()
assert text.count('while [ "$count" -lt 30 ]; do') == 1
text = text.replace('while [ "$count" -lt 30 ]; do',
    '# Asynchronous UFS/provider probes can outlast the former 30-second limit.\n'
    '    while [ "$count" -lt 300 ]; do')
helper.write_text(text)
(out/'rootfs-helper-before').write_bytes(original)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(out/'preparation.json').write_text(json.dumps(dict(
    kernel_build=112, baseline=111, config_delta=['CONFIG_INITRAMFS_SOURCE','CONFIG_LOG_BUF_SHIFT'],
    log_buffer_bytes=1048576, userdata_discovery_wait_seconds=300,
    rootfs_helper_before_sha256=hashlib.sha256(original).hexdigest(),
    rootfs_helper_after_sha256=sha(helper), slpi_auto_boot=False,
    boot_firmware_unchanged=True, flash_partitions=['logdump'],
    userdata_reformatted=False, goal_complete=False), indent=2)+'\n')
print('KERNEL112_ISOLATED_LOG_BUFFER_AND_ROOT_WAIT_PREPARED')
