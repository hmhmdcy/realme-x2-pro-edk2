from pathlib import Path
out=Path('/mnt/e/edk2-samurai-out/kernel103')
for name in ('Image-audio','dtb-audio','cpio-after','config-after','audio-target-build.log','kernel-build.log'):
    source=out/name;target=out/(name+'.first-environment')
    assert source.is_file() and not target.exists()
    source.rename(target)
print('FIRST_BUILD_RETAINED; rebuild with the original Rust detector on PATH')
