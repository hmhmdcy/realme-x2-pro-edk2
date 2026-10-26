from pathlib import Path
import subprocess
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
out = Path('/mnt/e/edk2-samurai-out/kernel97')
for name in ('coexistence-test.sh', 'verify-network.sh', 'start-traffic.sh', 'wifi-traffic-server.c', 'wifi-traffic-client.ps1'):
    source = (ref.parent / 'kernel96' / name).read_text().replace('k96', 'k97').replace('18096', '18097')
    if name in ('verify-network.sh', 'start-traffic.sh'):
        source = source.replace('initial|recovery|five-ghz', 'initial|initial-retry1|recovery|five-ghz')
    if name == 'verify-network.sh':
        source = source.replace('initial-retry1|recovery|five-ghz)', 'initial-retry1|recovery|five-ghz|five-ghz-retry1)')
    if name == 'wifi-traffic-server.c':
        source = source.replace('if (strcmp(phase,"initial") &&', 'if (strcmp(phase,"initial") && strcmp(phase,"initial-retry1") &&')
    target = ref / name
    assert not target.exists()
    target.write_text(source)
    if name.endswith('.sh'):
        subprocess.run(['sh', '-n', str(target)], check=True)
target = out / 'wifi-traffic-server'
assert not target.exists()
subprocess.run(['aarch64-linux-gnu-gcc', '-O2', '-D_GNU_SOURCE', '-Wall', '-Wextra', '-Werror', '-static', str(ref / 'wifi-traffic-server.c'), '-o', str(target)], check=True)
print('Bounded dual-band regression tools prepared')
