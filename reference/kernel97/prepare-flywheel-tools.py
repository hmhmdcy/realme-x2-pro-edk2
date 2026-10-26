from pathlib import Path
import subprocess
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
for name in ('flash-connectivity.ps1', 'reboot-f1.ps1', 'read-eud.ps1', 'stop-connectivity.sh', 'scp-private.ps1'):
    source = (ref.parent / 'kernel96' / name).read_text()
    source = source.replace('kernel96', 'kernel97').replace('K96', 'K97').replace('k96', 'k97')
    if name == 'flash-connectivity.ps1':
        source = source.replace('$audit.kernel_build -ne 95', '$audit.kernel_build -ne 96')
        source = source.replace('$audit.embedded_wifi_credentials -or', '$audit.embedded_wifi_credentials -or $audit.embedded_device_addresses -or')
    target = ref / name
    assert not target.exists()
    target.write_text(source)
    if name.endswith('.sh'):
        subprocess.run(['sh', '-n', str(target)], check=True)
print('Stage97 flywheel tools prepared; private identities remain external')
