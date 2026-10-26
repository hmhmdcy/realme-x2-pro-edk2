from pathlib import Path
import ast
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180')
names = ['capture-acoustic.py', 'analyze-acoustic.py', 'test-desktop-duplex.py', 'analyze-desktop.py']
for name in names:
    s = (ref.parent / 'kernel178' / name).read_text()
    s = s.replace('k178', 'k180').replace('stage=178', 'stage=180')
    s = s.replace('dmic0-ucm178-low24', 'dmic0-ucm180-low24').replace("startswith('#176 ')", "startswith('#180 ')")
    ast.parse(s)
    (ref / name).write_text(s)
with tarfile.open(out / 'acoustic-tools-private.tar', 'w') as archive:
    for name in ('capture-acoustic.py', 'test-desktop-duplex.py'):
        archive.add(ref / name, arcname='k180-' + name)
print('K180_ACOUSTIC_TOOLS_PREPARED')
