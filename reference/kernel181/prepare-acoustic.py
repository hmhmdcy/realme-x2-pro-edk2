from pathlib import Path
import ast
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel181')
names = ['capture-acoustic.py','analyze-acoustic.py','test-desktop-duplex.py','analyze-desktop.py']
for name in names:
    s = (ref.parent/'kernel180'/name).read_text()
    s = s.replace('k180','k181').replace('stage=180','stage=181').replace('kernel_build=180','kernel_build=181')
    s = s.replace('dmic0-ucm180-low24','dmic0-ucm181-low24').replace("startswith('#180 ')","startswith('#181 ')")
    s = s.replace("original_capture_report_kernel_build=report['kernel_build'],capture_boot_matched_verified_runtime180=True,",'')
    ast.parse(s);(ref/name).write_text(s)
with tarfile.open(out/'acoustic-tools-private.tar','w') as archive:
    for name in ('capture-acoustic.py','test-desktop-duplex.py'):
        archive.add(ref/name,arcname='k181-'+name)
print('K181_ACOUSTIC_TOOLS_PREPARED')
