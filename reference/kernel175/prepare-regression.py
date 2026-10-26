from pathlib import Path
import ast, tarfile

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175')
names=['capture-acoustic.py','analyze-acoustic.py','test-desktop-duplex.py','analyze-desktop.py','test-capture-stop.py']
for name in names:
    s=(ref.parent/'kernel174'/name).read_text().replace('kernel174','kernel175').replace('k174','k175').replace('stage=174','stage=175').replace('kernel_build=174','kernel_build=175')
    s=s.replace("startswith('#174 ')","startswith('#175 ')").replace('k175-runtime-v2/boot-id-private.txt','k175-runtime/boot-id-private.txt').replace('k175-stop-v2','k175-stop').replace('dmic0-ucm174-low24','dmic0-ucm175-low24')
    ast.parse(s);(ref/name).write_text(s)
with tarfile.open(out/'regression-tools-private.tar','w') as ar:
    for name in ['test-reprobe.py','test-capture-stop.py','capture-acoustic.py','test-desktop-duplex.py']:
        ar.add(ref/name,arcname='k175-'+name)
print('K175_REGRESSION_PREPARED',flush=True)
