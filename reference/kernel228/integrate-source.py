"""Publish the accepted full source and incremental patch with explicit deployment states."""
from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parents[2]
ref = Path(__file__).resolve().parent
destination = root / 'linux-port/ssc/kernel'
assert not destination.exists()
destination.mkdir()
source = Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/misc/fastrpc.c').read_bytes()
assert hashlib.sha256(source).hexdigest() == 'f378afedc84d4d0cc29166686210fbf706ea16be59dd4270cab2f3c3ac5faec8'
(destination / 'fastrpc.c').write_bytes(source)
shutil.copyfile(root / 'reference/kernel227/fastrpc-publication-lifetime.patch', destination / '0001-fastrpc-publication-lifetime.patch')
build = json.loads((ref / 'intree-build-validation.json').read_text())
lock = dict(stage=228, profile='incremental FastRPC on accepted189 same-ABI kernel183 tree',
            kernel_release='7.3.0-rc6-rmx1931-samurai-k132+', source_file='fastrpc.c',
            source_sha256=build['source_sha256'], patch='0001-fastrpc-publication-lifetime.patch',
            patch_sha256=hashlib.sha256((destination / '0001-fastrpc-publication-lifetime.patch').read_bytes()).hexdigest(),
            patch_base189_source_sha256='41c8db5c323404dbd6230a43206ff573e0f5ad327574d3ffe94cc741ca6da347',
            freezer189_preserved=True, real_in_tree_build=build,
            loaded_this_boot=dict(module_sha256='7ca5d442fb8351f841dcae3d16e4f981d9b08e7326b42c674f7ceaf4f08bdc0a',
                                  intree=False, taint=4096, native_sensor_and_pin_tests_passed=True),
            rootfs_default=dict(module_sha256=build['module_sha256'], module_bytes=build['module_bytes'],
                                intree=True, staged=True, clean_boot_verified=False),
            not_proven=['SSR/DMA drain','reclaim -22','physical sensor accuracy','full rootfs rebuild'])
(destination / 'source-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
print(json.dumps(dict(accepted_full_source_published=True, incremental_patch_locked=True, clean_intree_boot_pending=True)))
