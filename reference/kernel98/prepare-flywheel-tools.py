from pathlib import Path
import subprocess
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
for name in ('flash-connectivity.ps1','reboot-f1.ps1','read-eud.ps1','stop-connectivity.sh','scp-private.ps1'):
    text = (ref.parent/'kernel97'/name).read_text().replace('kernel97','kernel98').replace('K97','K98').replace('k97','k98')
    if name=='flash-connectivity.ps1': text=text.replace('$audit.kernel_build -ne 96','$audit.kernel_build -ne 97')
    assert not (ref/name).exists()
    (ref/name).write_text(text)
    if name.endswith('.sh'): subprocess.run(['sh','-n',str(ref/name)],check=True)
print('Stage98 flywheel tools prepared')
