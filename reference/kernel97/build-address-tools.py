from pathlib import Path
import hashlib, json, subprocess

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
out = Path('/mnt/e/edk2-samurai-out/kernel97')
qrtr = out.parent / 'kernel88/qrtr'
for name, sources, extra in (
    ('samurai-dms-mac-read', ['dms-mac-read.c'], ['-I' + str(qrtr / 'include'), str(qrtr / 'lib/qrtr.c'), str(qrtr / 'lib/logging.c')]),
    ('samurai-bt-address', ['samurai-bt-address.c'], []),
):
    target = out / name
    assert not target.exists()
    subprocess.run(['aarch64-linux-gnu-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static', *[str(ref / p) for p in sources], *extra, '-o', str(target)], check=True)
for name in ('samurai-radio-address', 'samurai-bluetooth'):
    subprocess.run(['sh', '-n', str(ref / name)], check=True)
report = {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in ('samurai-dms-mac-read', 'samurai-bt-address')}
(out / 'address-tools-build.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
