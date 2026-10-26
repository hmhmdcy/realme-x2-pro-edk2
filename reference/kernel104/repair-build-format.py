from pathlib import Path
import difflib
root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel104'
out = Path('/mnt/e/edk2-samurai-out/kernel104')
k = Path('/home/cy122/x2pro-linux/linux')
for n in ('Image-audio', 'dtb-audio', 'cpio-after', 'config-after', 'audio-target-build.log', 'kernel-build.log', 'olddefconfig.log'):
    assert (out / n).is_file() and not (out / (n + '.first-format')).exists()
    (out / n).rename(out / (n + '.first-format'))
for p in (k / 'sound/soc/qcom/qdsp6/q6core.c', ref / 'q6core.c.after', ref / 'prepare-source.py'):
    s = p.read_text()
    assert s.count('bytes=%zu') == 1
    p.write_text(s.replace('bytes=%zu', 'bytes=%d'))
before = (out / 'q6core-before.c').read_text()
after = (k / 'sound/soc/qcom/qdsp6/q6core.c').read_text()
target = 'sound/soc/qcom/qdsp6/q6core.c'
(ref / 'q6core.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + target, tofile='b/' + target)))
p = ref / 'split-backups.sh'
(out / 'split-backups.first-guard.sh').write_bytes(p.read_bytes())
p.write_text(p.read_text().replace('#101 SMP PREEMPT', '#102 SMP PREEMPT'))
print('FIRST_WARNING_BUILD_PRESERVED_FORMAT_AND_SPLIT_GUARD_CORRECTED')
