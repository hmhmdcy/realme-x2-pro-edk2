from pathlib import Path
import ast, tarfile

ref = Path(__file__).parent
out = Path('E:/edk2-samurai-out/kernel177')
names = ['capture-acoustic.py', 'analyze-acoustic.py', 'test-desktop-duplex.py', 'analyze-desktop.py', 'test-capture-stop.py']
for name in names:
    s = (ref.parent / 'kernel176' / name).read_text()
    s = s.replace('k176', 'k177').replace('stage=176', 'stage=177')
    s = s.replace('dmic0-ucm176-low24', 'dmic0-ucm177-low24')
    # The validation stage changes; the deployed kernel remains build176.
    assert "startswith('#176 ')" in s or name.startswith('analyze-')
    ast.parse(s)
    (ref / name).write_text(s)
with tarfile.open(out / 'post-suspend-tools-private.tar', 'w') as ar:
    for name in ['capture-acoustic.py', 'test-desktop-duplex.py', 'test-capture-stop.py', 'collect-pre-regression.py']:
        ar.add(ref / name, arcname='k177-' + name)
print('POST_SUSPEND_REGRESSION_PREPARED')
