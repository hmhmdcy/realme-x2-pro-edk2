from pathlib import Path
import ast, tarfile

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel176')
names=['capture-acoustic.py','analyze-acoustic.py','test-desktop-duplex.py','analyze-desktop.py','test-capture-stop.py','test-reprobe-v2.py']
for name in names:
    s=(ref.parent/'kernel175'/name).read_text().replace('kernel175','kernel176').replace('k175','k176').replace('stage=175','stage=176').replace('kernel_build=175','kernel_build=176')
    s=s.replace("startswith('#175 ')","startswith('#176 ')").replace('dmic0-ucm175-low24','dmic0-ucm176-low24').replace('k176-reprobe-v2','k176-reprobe')
    if name=='test-reprobe-v2.py':
        s=s.replace("enumerate(['codec','codec','mfd','mfd'])","enumerate(['codec','codec'] + ['mfd'] * 8)")
        s=s.replace("'irq_chip_error':'Failed to add IRQ chip'","'irq_chip_error':'Failed to add IRQ chip','ngd_error_interrupt':'Error Interrupt received','transfer_timeout':'failed:-110','bringup_error':'Failed to bring up WCD934X:'")
    ast.parse(s);(ref/('test-reprobe.py' if name=='test-reprobe-v2.py' else name)).write_text(s)
with tarfile.open(out/'regression-tools-private.tar','w') as ar:
    for name in ['test-reprobe.py','test-capture-stop.py','capture-acoustic.py','test-desktop-duplex.py']:ar.add(ref/name,arcname='k176-'+name)
print('K176_REGRESSION_TOOLS_PREPARED',flush=True)
