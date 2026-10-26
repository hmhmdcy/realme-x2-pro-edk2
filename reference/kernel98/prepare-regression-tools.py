from pathlib import Path
import subprocess

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
out = Path('/mnt/e/edk2-samurai-out/kernel98')
for name in ('verify-network.sh','start-traffic.sh','wifi-traffic-server.c','wifi-traffic-client.ps1'):
    text = (ref.parent/'kernel97'/name).read_text().replace('k97','k98').replace('18097','18098')
    assert not (ref/name).exists()
    (ref/name).write_text(text)
    if name.endswith('.sh'): subprocess.run(['sh','-n',str(ref/name)],check=True)
subprocess.run(['aarch64-linux-gnu-gcc','-D_GNU_SOURCE','-O2','-Wall','-Wextra','-Werror','-static',str(ref/'wifi-traffic-server.c'),'-o',str(out/'wifi-traffic-server')],check=True)
print('Stage98 bounded Wi-Fi traffic tools prepared')
