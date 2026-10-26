from pathlib import Path
import ast, tarfile

ref = Path(__file__).parent
out = Path('E:/edk2-samurai-out/kernel178')
for name in ['capture-acoustic.py', 'analyze-acoustic.py', 'test-desktop-duplex.py', 'analyze-desktop.py']:
    s = (ref.parent / 'kernel177' / name).read_text().replace('k177', 'k178').replace('stage=177', 'stage=178')
    s = s.replace('dmic0-ucm177-low24', 'dmic0-ucm178-low24')
    ast.parse(s); (ref / name).write_text(s)
with tarfile.open(out / 'acoustic-tools-private.tar', 'w') as ar:
    for name in ['capture-acoustic.py', 'test-desktop-duplex.py']:
        ar.add(ref / name, arcname='k178-' + name)
print('ACOUSTIC178_TOOLS_PREPARED')
