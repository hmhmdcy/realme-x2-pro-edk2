from pathlib import Path
import ast, tarfile

ref=Path(__file__).parent
out=Path('/mnt/e/edk2-samurai-out/kernel174')
names=['capture-acoustic.py','analyze-acoustic.py','test-desktop-duplex.py','analyze-desktop.py']
for name in names:
    s=(ref.parent/'kernel173'/name).read_text().replace('k173','k174').replace('kernel173','kernel174').replace('stage=173','stage=174').replace('kernel_build=172','kernel_build=174')
    s=s.replace("startswith('#172 ')","startswith('#174 ')").replace('k174-source/boot-id-private.txt','k174-runtime/boot-id-private.txt').replace('dmic0-ucm173-low24','dmic0-ucm174-low24')
    ast.parse(s);(ref/name).write_text(s)
with tarfile.open(out/'regression-tools-private.tar','w') as ar:
    for name in ['capture-acoustic.py','test-desktop-duplex.py','test-capture-stop.py']: ar.add(ref/name,arcname='k174-'+name)
print('K174_REGRESSION_TOOLS_PREPARED',flush=True)
